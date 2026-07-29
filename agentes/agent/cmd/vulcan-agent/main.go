package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"

	agentapp "github.com/lanfuture/vulcan/agentes/agent/internal/app"
	"github.com/lanfuture/vulcan/agentes/agent/internal/config"
	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	"github.com/lanfuture/vulcan/agentes/agent/internal/identity"
	vlogging "github.com/lanfuture/vulcan/agentes/agent/internal/logging"
	"github.com/lanfuture/vulcan/agentes/agent/internal/policy"
	"github.com/lanfuture/vulcan/agentes/agent/internal/queue"
	"github.com/lanfuture/vulcan/agentes/agent/internal/service"
	"github.com/lanfuture/vulcan/agentes/agent/internal/transport"
	"github.com/shirou/gopsutil/v4/host"
)

var (
	version   = "0.2.0-dev"
	commitSHA = "local"
	buildTime = "unknown"
)

func main() {
	if err := execute(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "vulcan-agent:", err)
		os.Exit(1)
	}
}

func execute(arguments []string) error {
	if len(arguments) == 0 {
		printUsage()
		return errors.New("a command is required")
	}
	switch arguments[0] {
	case "enroll":
		return enroll(arguments[1:])
	case "run":
		return run()
	case "status":
		return statusCommand(false)
	case "health":
		return statusCommand(true)
	case "diagnostics":
		return diagnostics()
	case "policy":
		return policyCommand(arguments[1:])
	case "logs":
		return logsCommand(arguments[1:])
	case "test-connection":
		return testConnection()
	case "unenroll":
		return unenroll(arguments[1:])
	case "install-service":
		return service.Install()
	case "uninstall-service":
		return service.Uninstall()
	case "protect-data":
		return service.ProtectData(runtimePaths().ConfigDir)
	case "configure-recovery":
		return service.ConfigureRecovery()
	case "version", "--version", "-version":
		fmt.Printf("Vulcan Agent %s commit=%s built=%s go=%s\n", version, commitSHA, buildTime, runtime.Version())
		return nil
	case "help", "--help", "-h":
		printUsage()
		return nil
	default:
		printUsage()
		return fmt.Errorf("unknown command %q", arguments[0])
	}
}

func enroll(arguments []string) error {
	flags := flag.NewFlagSet("enroll", flag.ContinueOnError)
	serverURL := flags.String("server", "", "URL HTTPS do Vulcan")
	token := flags.String("token", os.Getenv("VULCAN_ENROLLMENT_TOKEN"), "token de enrollment de curta duração")
	tokenFile := flags.String("token-file", "", "arquivo protegido contendo o token de enrollment")
	profileValue := flags.String("profile", "workstation", "workstation, server ou collector")
	allowLoopback := flags.Bool("allow-insecure-loopback", false, "permite HTTP apenas em localhost para desenvolvimento")
	allowPrivateNetwork := flags.Bool(
		"allow-insecure-private-network",
		false,
		"permite HTTP somente para endereço IP privado, mediante aceite explícito",
	)
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if *tokenFile != "" {
		data, readErr := os.ReadFile(*tokenFile)
		if readErr != nil {
			return fmt.Errorf("read enrollment token file: %w", readErr)
		}
		*token = strings.TrimSpace(string(data))
	}
	if *serverURL == "" || *token == "" {
		return errors.New("--server and an enrollment token (--token, --token-file or VULCAN_ENROLLMENT_TOKEN) are required")
	}
	profile := contracts.Profile(*profileValue)
	if !profile.Valid() {
		return errors.New("--profile must be workstation, server or collector")
	}
	parsed, err := url.Parse(*serverURL)
	if err != nil {
		return err
	}
	loopbackHTTP := parsed.Scheme == "http" &&
		(parsed.Hostname() == "localhost" || parsed.Hostname() == "127.0.0.1" || parsed.Hostname() == "::1")
	privateHTTP := parsed.Scheme == "http" && isPrivateIPAddress(parsed.Hostname())
	if parsed.Scheme != "https" &&
		!(loopbackHTTP && *allowLoopback) &&
		!(privateHTTP && *allowPrivateNetwork) {
		return errors.New(
			"HTTPS is mandatory; private-address HTTP requires --allow-insecure-private-network",
		)
	}
	paths := runtimePaths()
	if _, err := os.Stat(paths.ConfigFile()); err == nil {
		return errors.New("agent is already enrolled; run unenroll before creating a new identity")
	}
	if err := paths.Ensure(); err != nil {
		return err
	}
	material, err := identity.LoadOrCreate(paths.DataDir)
	if err != nil {
		return err
	}
	deviceFingerprint, err := identity.DeviceFingerprint()
	if err != nil {
		return err
	}
	hostInfo, err := host.Info()
	if err != nil {
		return err
	}
	transportOptions := []transport.Option{}
	if *allowPrivateNetwork {
		transportOptions = append(transportOptions, transport.WithInsecurePrivateNetwork())
	}
	client, err := transport.New(
		strings.TrimRight(*serverURL, "/"),
		"",
		material.PrivateKey,
		version,
		transportOptions...,
	)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	response, err := client.Enroll(ctx, contracts.EnrollmentRequest{
		EnrollmentToken:      *token,
		PublicKey:            identity.PublicKeyBase64(material),
		PublicKeyFingerprint: identity.Fingerprint(material),
		DeviceFingerprint:    deviceFingerprint,
		Hostname:             hostInfo.Hostname,
		OperatingSystem:      hostInfo.Platform + " " + hostInfo.PlatformVersion,
		Architecture:         runtime.GOARCH,
		AgentVersion:         version,
		Profile:              profile,
		Metadata: map[string]any{
			"kernelVersion": hostInfo.KernelVersion,
			"installMode":   installMode(),
		},
	})
	if err != nil {
		return err
	}
	policyStore, err := policy.NewStore(
		paths.DataDir,
		response.PolicySigningPublicKey,
		response.TenantID,
		response.AgentID,
		profile,
	)
	if err != nil {
		return err
	}
	effective, err := policyStore.Apply(response.Policy)
	if err != nil {
		return fmt.Errorf("server returned an invalid signed policy: %w", err)
	}
	cfg := config.Config{
		ServerURL:                   strings.TrimRight(*serverURL, "/"),
		Profile:                     profile,
		TenantID:                    response.TenantID,
		DeviceID:                    response.DeviceID,
		AgentID:                     response.AgentID,
		PolicySigningPublicKey:      response.PolicySigningPublicKey,
		PolicyRevision:              effective.Revision,
		PolicyStatus:                "applied",
		AllowInsecureLoopback:       *allowLoopback,
		AllowInsecurePrivateNetwork: *allowPrivateNetwork,
		EnrolledAt:                  time.Now().UTC(),
	}
	if err := config.Save(paths, cfg); err != nil {
		return err
	}
	fmt.Printf("Enrollment concluído: agent=%s device=%s profile=%s status=%s\n",
		response.AgentID,
		response.DeviceID,
		profile,
		response.Status,
	)
	return nil
}

func run() error {
	runAgent := func(ctx context.Context) error {
		instance, err := agentapp.New(runtimePaths(), version)
		if err != nil {
			return err
		}
		return instance.Run(ctx)
	}
	if handled, err := service.RunIfService(runAgent); handled {
		return err
	} else if err != nil {
		return err
	}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	return runAgent(ctx)
}

func statusCommand(checkConnection bool) error {
	paths := runtimePaths()
	cfg, err := config.Load(paths)
	if err != nil {
		return err
	}
	payload := map[string]any{
		"status":            "enrolled",
		"version":           version,
		"profile":           cfg.Profile,
		"tenantId":          cfg.TenantID,
		"deviceId":          cfg.DeviceID,
		"agentId":           cfg.AgentID,
		"server":            cfg.ServerURL,
		"policyRevision":    cfg.PolicyRevision,
		"policyStatus":      cfg.PolicyStatus,
		"transportSecurity": transportSecurity(cfg),
	}
	eventQueue, queueErr := queue.Open(paths.DataDir, queue.Limits{})
	if queueErr == nil {
		defer eventQueue.Close()
		stats, statsErr := eventQueue.Stats(context.Background())
		if statsErr == nil {
			payload["queue"] = stats
		}
	}
	if checkConnection {
		connectionError := testConnection()
		payload["connection"] = "ok"
		if connectionError != nil {
			payload["connection"] = "failed"
			payload["connectionError"] = connectionError.Error()
		}
	}
	return printJSON(payload)
}

func diagnostics() error {
	paths := runtimePaths()
	cfg, err := config.Load(paths)
	if err != nil {
		return err
	}
	material, identityErr := identity.LoadOrCreate(paths.DataDir)
	policyStatus := "ok"
	if identityErr == nil {
		store, storeErr := policy.NewStore(
			paths.DataDir,
			cfg.PolicySigningPublicKey,
			cfg.TenantID,
			cfg.AgentID,
			cfg.Profile,
		)
		if storeErr != nil {
			policyStatus = storeErr.Error()
		} else if _, loadErr := store.Load(); loadErr != nil {
			policyStatus = loadErr.Error()
		}
	}
	connection := "ok"
	if connectionErr := testConnection(); connectionErr != nil {
		connection = connectionErr.Error()
	}
	identityStatus := "ok"
	if identityErr != nil || len(material.PrivateKey) == 0 {
		identityStatus = "invalid"
	}
	return printJSON(map[string]any{
		"version":           version,
		"commit":            commitSHA,
		"service":           service.Name,
		"profile":           cfg.Profile,
		"tenantId":          cfg.TenantID,
		"deviceId":          cfg.DeviceID,
		"agentId":           cfg.AgentID,
		"server":            cfg.ServerURL,
		"identity":          identityStatus,
		"policy":            policyStatus,
		"connection":        connection,
		"transportSecurity": transportSecurity(cfg),
		"clock":             time.Now().UTC().Format(time.RFC3339Nano),
		"operatingSystem":   runtime.GOOS,
		"architecture":      runtime.GOARCH,
		"configDir":         paths.ConfigDir,
		"dataDir":           paths.DataDir,
		"logDir":            paths.LogDir,
	})
}

func policyCommand(arguments []string) error {
	paths := runtimePaths()
	cfg, err := config.Load(paths)
	if err != nil {
		return err
	}
	store, err := policy.NewStore(
		paths.DataDir,
		cfg.PolicySigningPublicKey,
		cfg.TenantID,
		cfg.AgentID,
		cfg.Profile,
	)
	if err != nil {
		return err
	}
	effective, err := store.Load()
	if err != nil {
		return err
	}
	return printJSON(map[string]any{"revision": effective.Revision, "policy": effective.Document})
}

func logsCommand(arguments []string) error {
	flags := flag.NewFlagSet("logs", flag.ContinueOnError)
	lines := flags.Int("lines", 100, "quantidade de linhas estruturadas")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	path := filepath.Join(runtimePaths().LogDir, "agent.jsonl")
	entries, err := vlogging.Tail(path, *lines)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		fmt.Println(entry)
	}
	return nil
}

func testConnection() error {
	paths := runtimePaths()
	cfg, err := config.Load(paths)
	if err != nil {
		return err
	}
	material, err := identity.LoadOrCreate(paths.DataDir)
	if err != nil {
		return err
	}
	client, err := transport.New(cfg.ServerURL, cfg.AgentID, material.PrivateKey, version, transportOptions(cfg)...)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	return client.TestConnection(ctx)
}

func unenroll(arguments []string) error {
	flags := flag.NewFlagSet("unenroll", flag.ContinueOnError)
	reason := flags.String("reason", "Desinstalação autorizada do Vulcan Agent.", "motivo auditável")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if len(strings.TrimSpace(*reason)) < 5 {
		return errors.New("unenroll reason must contain at least five characters")
	}
	paths := runtimePaths()
	cfg, err := config.Load(paths)
	if err != nil {
		return err
	}
	material, err := identity.LoadOrCreate(paths.DataDir)
	if err != nil {
		return err
	}
	client, err := transport.New(cfg.ServerURL, cfg.AgentID, material.PrivateKey, version, transportOptions(cfg)...)
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := client.Unenroll(ctx, *reason); err != nil {
		return err
	}
	marker := filepath.Join(paths.DataDir, "unenrolled.json")
	data, _ := json.MarshalIndent(map[string]any{
		"agentId":      cfg.AgentID,
		"deviceId":     cfg.DeviceID,
		"unenrolledAt": time.Now().UTC(),
		"reason":       *reason,
	}, "", "  ")
	if err := os.WriteFile(marker, append(data, '\n'), 0o600); err != nil {
		return err
	}
	fmt.Println("Identidade revogada no servidor. Pare e remova o serviço antes de apagar os dados locais.")
	return nil
}

func runtimePaths() config.Paths {
	paths := config.DefaultPaths()
	if value := os.Getenv("VULCAN_AGENT_CONFIG_DIR"); value != "" {
		paths.ConfigDir = value
	}
	if value := os.Getenv("VULCAN_AGENT_DATA_DIR"); value != "" {
		paths.DataDir = value
	}
	if value := os.Getenv("VULCAN_AGENT_LOG_DIR"); value != "" {
		paths.LogDir = value
	}
	return paths
}

func transportOptions(cfg config.Config) []transport.Option {
	if cfg.AllowInsecurePrivateNetwork {
		return []transport.Option{transport.WithInsecurePrivateNetwork()}
	}
	return nil
}

func transportSecurity(cfg config.Config) string {
	if cfg.AllowInsecurePrivateNetwork {
		return "http-private-network-explicit"
	}
	if cfg.AllowInsecureLoopback {
		return "http-loopback-development"
	}
	return "https"
}

func isPrivateIPAddress(hostname string) bool {
	address := net.ParseIP(hostname)
	return address != nil && address.IsPrivate()
}

func installMode() string {
	if runtime.GOOS == "windows" {
		return "windows-service"
	}
	if runningAsRoot() {
		return "systemd-system"
	}
	return "systemd-user"
}

func printJSON(value any) error {
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	encoder.SetEscapeHTML(false)
	return encoder.Encode(value)
}

func printUsage() {
	fmt.Print(`Vulcan Agent

Commands:
  enroll            registra uma nova identidade criptográfica
  run               inicia o ciclo de coleta, heartbeat e sincronização
  status            mostra estado local sem segredos
  health            valida estado local e conectividade
  diagnostics       executa diagnóstico seguro
  policy            mostra a política efetiva assinada
  logs              mostra logs JSON rotativos
  test-connection   testa o gateway Vulcan
  unenroll          revoga a identidade no servidor
  install-service   instala o serviço Windows
  uninstall-service remove o serviço Windows
  version           mostra versão, commit e toolchain
`)
}

func init() {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, nil)))
}
