//go:build windows

package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"syscall"
	"time"
	"unsafe"

	_ "modernc.org/sqlite"

	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/svc"
)

const (
	serviceName = "VulcanAgent"
	displayName = "Vulcan Agent Service"
	version     = "0.2.0"
)

type AgentPolicy struct {
	CollectAppName           bool   `json:"collectAppName"`
	CollectWindowTitle       bool   `json:"collectWindowTitle"`
	CollectIdleTime          bool   `json:"collectIdleTime"`
	CollectSessionEvents     bool   `json:"collectSessionEvents"`
	CollectBrowserDomain     bool   `json:"collectBrowserDomain"`
	CollectBrowserURL        bool   `json:"collectBrowserUrl"`
	CollectBrowserHistory    bool   `json:"collectBrowserHistory"`
	CollectBrowserPageTitle  bool   `json:"collectBrowserPageTitle"`
	CollectProcessList       bool   `json:"collectProcessList"`
	CollectSystemMetrics     bool   `json:"collectSystemMetrics"`
	RedactSensitiveTerms     bool   `json:"redactSensitiveTerms"`
	BrowserHistoryInterval   int    `json:"browserHistoryIntervalSeconds"`
	BrowserHistoryLookback   int    `json:"browserHistoryLookbackMinutes"`
	BrowserHistoryMaxEvents  int    `json:"browserHistoryMaxEvents"`
	SyncIntervalSeconds      int    `json:"syncIntervalSeconds"`
	HeartbeatIntervalSeconds int    `json:"heartbeatIntervalSeconds"`
	OfflineQueueEnabled      bool   `json:"offlineQueueEnabled"`
	MaxOfflineQueueSize      int    `json:"maxOfflineQueueSize"`
	AllowUserPause           bool   `json:"allowUserPause"`
	ShowTrayStatus           bool   `json:"showTrayStatus"`
	PrivacyMode              string `json:"privacyMode"`
	IdleThresholdSeconds     int    `json:"idleThresholdSeconds"`
}

type Config struct {
	BackendURL               string      `json:"backendUrl"`
	TenantID                 string      `json:"tenantId"`
	EnrollmentToken          string      `json:"enrollmentToken"`
	DeviceID                 string      `json:"deviceId"`
	MachineFingerprint       string      `json:"machineFingerprint"`
	Hostname                 string      `json:"hostname"`
	OSUser                   string      `json:"osUser"`
	OSVersion                string      `json:"osVersion"`
	LinkedUser               string      `json:"linkedUser,omitempty"`
	UserID                   string      `json:"userId,omitempty"`
	MembershipID             string      `json:"membershipId,omitempty"`
	RoleLevel                string      `json:"roleLevel,omitempty"`
	Department               string      `json:"department,omitempty"`
	ManagerMembershipID      string      `json:"managerMembershipId,omitempty"`
	Note                     string      `json:"note,omitempty"`
	CollectWindowTitle       bool        `json:"collectWindowTitle"`
	Policy                   AgentPolicy `json:"policy"`
	HeartbeatIntervalSeconds int         `json:"heartbeatIntervalSeconds"`
	SyncIntervalSeconds      int         `json:"syncIntervalSeconds"`
	InstalledAt              string      `json:"installedAt"`
}

type AgentEvent struct {
	EventID         string                 `json:"eventId"`
	EventType       string                 `json:"eventType"`
	AppName         string                 `json:"appName"`
	WindowTitle     string                 `json:"windowTitle,omitempty"`
	Category        string                 `json:"category,omitempty"`
	StartedAt       string                 `json:"startedAt"`
	EndedAt         string                 `json:"endedAt"`
	DurationSeconds int64                  `json:"durationSeconds"`
	OSUser          string                 `json:"osUser,omitempty"`
	Metadata        map[string]interface{} `json:"metadata,omitempty"`
}

type enrollRequest struct {
	TenantID            string `json:"tenantId"`
	EnrollmentToken     string `json:"enrollmentToken"`
	Hostname            string `json:"hostname"`
	OSUser              string `json:"osUser,omitempty"`
	OSVersion           string `json:"osVersion,omitempty"`
	DeviceID            string `json:"deviceId,omitempty"`
	MachineFingerprint  string `json:"machineFingerprint"`
	AgentVersion        string `json:"agentVersion"`
	LinkedUser          string `json:"linkedUser,omitempty"`
	UserID              string `json:"userId,omitempty"`
	MembershipID        string `json:"membershipId,omitempty"`
	RoleLevel           string `json:"roleLevel,omitempty"`
	Department          string `json:"department,omitempty"`
	ManagerMembershipID string `json:"managerMembershipId,omitempty"`
	Note                string `json:"note,omitempty"`
}

type enrollResponse struct {
	Accepted                 bool   `json:"accepted"`
	DeviceID                 string `json:"deviceId"`
	HeartbeatIntervalSeconds int    `json:"heartbeatIntervalSeconds"`
	SyncIntervalSeconds      int    `json:"syncIntervalSeconds"`
}

type heartbeatRequest struct {
	TenantID           string                 `json:"tenantId"`
	EnrollmentToken    string                 `json:"enrollmentToken"`
	DeviceID           string                 `json:"deviceId,omitempty"`
	MachineFingerprint string                 `json:"machineFingerprint"`
	Hostname           string                 `json:"hostname"`
	AgentVersion       string                 `json:"agentVersion"`
	Status             string                 `json:"status"`
	QueueDepth         int                    `json:"queueDepth"`
	LastError          string                 `json:"lastError,omitempty"`
	Metadata           map[string]interface{} `json:"metadata,omitempty"`
}

type syncRequest struct {
	TenantID           string       `json:"tenantId"`
	EnrollmentToken    string       `json:"enrollmentToken"`
	DeviceID           string       `json:"deviceId,omitempty"`
	MembershipID       string       `json:"membershipId,omitempty"`
	MachineFingerprint string       `json:"machineFingerprint"`
	Hostname           string       `json:"hostname"`
	Events             []AgentEvent `json:"events"`
}

type syncResponse struct {
	Accepted bool `json:"accepted"`
	Received int  `json:"received"`
	Stored   int  `json:"stored"`
}

type logEntry struct {
	Level     string                 `json:"level"`
	Message   string                 `json:"message"`
	CreatedAt string                 `json:"createdAt"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

type logsRequest struct {
	TenantID           string     `json:"tenantId"`
	EnrollmentToken    string     `json:"enrollmentToken"`
	DeviceID           string     `json:"deviceId,omitempty"`
	MachineFingerprint string     `json:"machineFingerprint"`
	Logs               []logEntry `json:"logs"`
}

type browserProfile struct {
	Browser string
	Engine  string
	Profile string
	Path    string
}

type browserVisit struct {
	URL       string
	Title     string
	VisitedAt time.Time
}

type browserHistoryState struct {
	Seen            []string `json:"seen"`
	LastCollectedAt string   `json:"lastCollectedAt,omitempty"`
}

const windowsEpochOffsetSeconds = 11644473600

var sensitivePatterns = []string{
	"password", "senha", "secret", "token", "cookie", "login", "log in", "sign in",
	"whatsapp", "telegram", "signal", "bank", "banco", "cpf", "cnpj", "cartao", "card",
	"private", "privado", "confidential", "confidencial",
}

var adultDomainPatterns = []string{
	"porn", "xvideos", "xnxx", "xhamster", "redtube", "youporn", "tube8", "spankbang",
	"brazzers", "sex", "adult", "onlyfans", "privacy.com.br",
}

type agentService struct {
	configPath string
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		return
	}

	switch strings.ToLower(os.Args[1]) {
	case "install":
		exit(installCommand(os.Args[2:]))
	case "uninstall":
		exit(uninstallCommand(os.Args[2:]))
	case "repair":
		exit(repairCommand(os.Args[2:]))
	case "status":
		exit(statusCommand(os.Args[2:]))
	case "service":
		exit(serviceCommand())
	case "collector":
		exit(collectorCommand())
	case "tray":
		exit(trayCommand())
	case "enroll":
		exit(enrollCommand())
	case "heartbeat":
		exit(heartbeatCommand())
	case "sync":
		exit(syncCommand())
	case "run":
		exit(runForegroundCollector())
	default:
		fmt.Printf("unknown command: %s\n\n", os.Args[1])
		printUsage()
		os.Exit(2)
	}
}

func exit(err error) {
	if err == nil {
		return
	}
	fmt.Fprintln(os.Stderr, "Vulcan Agent:", err)
	os.Exit(1)
}

func printUsage() {
	fmt.Println(`Vulcan Agent for Windows

Commands:
  install     Install service, session collector task and local config.
  uninstall   Stop and remove service and scheduled tasks.
  repair      Recreate service recovery and scheduled tasks from current config.
  status      Print agent config, queue depth and service status.
  service     Internal Windows service entrypoint.
  collector   Internal per-user foreground application collector.
  tray        Placeholder user helper process for future tray UI.
  enroll      Enroll current machine with the Vulcan backend.
  heartbeat   Send a heartbeat once.
  sync        Sync queued events once.
  run         Run collector in foreground for local diagnostics.`)
}

func installCommand(args []string) error {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	backendURL := fs.String("BackendUrl", "http://localhost:3001", "Vulcan backend URL")
	tenantID := fs.String("TenantId", "", "tenant UUID")
	enrollmentToken := fs.String("EnrollmentToken", "", "agent enrollment token")
	linkedUser := fs.String("LinkedUser", currentUser(), "human-readable linked user")
	userID := fs.String("UserId", "", "optional user profile UUID")
	membershipID := fs.String("MembershipId", "", "optional membership UUID")
	roleLevel := fs.String("RoleLevel", "Operador", "organizational level or role label")
	department := fs.String("Department", "", "department label")
	managerMembershipID := fs.String("ManagerMembershipId", "", "optional manager membership UUID")
	note := fs.String("Note", "", "installation note")
	collectWindowTitle := fs.Bool("CollectWindowTitle", false, "collect active window title after privacy filtering")
	collectBrowserDomain := fs.Bool("CollectBrowserDomain", false, "collect browser domain when available by policy")
	collectBrowserURL := fs.Bool("CollectBrowserUrl", false, "collect browser URL without querystring or fragment")
	collectBrowserHistory := fs.Bool("CollectBrowserHistory", false, "collect recent browser history with sanitized URL")
	collectProcessList := fs.Bool("CollectProcessList", false, "collect summarized process list and use process fallback")
	corporateMonitoring := fs.Bool("CorporateMonitoring", false, "enable maximum corporate monitoring policy without keystrokes, screenshots, audio, webcam, clipboard, cookies or tokens")
	syncInterval := fs.Int("SyncInterval", 30, "sync interval in seconds")
	heartbeatInterval := fs.Int("HeartbeatInterval", 60, "heartbeat interval in seconds")
	installDir := fs.String("InstallDir", defaultInstallDir(), "install directory")
	dataDir := fs.String("DataDir", defaultDataDir(), "data directory")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if strings.TrimSpace(*tenantID) == "" {
		return errors.New("TenantId is required")
	}
	if strings.TrimSpace(*enrollmentToken) == "" {
		return errors.New("EnrollmentToken is required")
	}

	if err := ensureAgentDirs(*dataDir); err != nil {
		return err
	}
	if err := os.MkdirAll(*installDir, 0755); err != nil {
		return err
	}

	exePath, err := copyInstallBinaries(*installDir)
	if err != nil {
		return err
	}

	policy := defaultAgentPolicy(*collectWindowTitle, maxInt(*syncInterval, 15), maxInt(*heartbeatInterval, 15), *corporateMonitoring)
	if *collectBrowserDomain {
		policy.CollectBrowserDomain = true
	}
	if *collectBrowserURL {
		policy.CollectBrowserURL = true
	}
	if *collectBrowserHistory {
		policy.CollectBrowserHistory = true
	}
	if *collectProcessList {
		policy.CollectProcessList = true
	}
	cfg := Config{
		BackendURL:               strings.TrimRight(*backendURL, "/"),
		TenantID:                 *tenantID,
		EnrollmentToken:          *enrollmentToken,
		DeviceID:                 uuidV4(),
		MachineFingerprint:       machineFingerprint(*tenantID, *backendURL),
		Hostname:                 hostname(),
		OSUser:                   currentUser(),
		OSVersion:                osVersion(),
		LinkedUser:               *linkedUser,
		UserID:                   *userID,
		MembershipID:             *membershipID,
		RoleLevel:                *roleLevel,
		Department:               *department,
		ManagerMembershipID:      *managerMembershipID,
		Note:                     *note,
		CollectWindowTitle:       *collectWindowTitle || *corporateMonitoring,
		Policy:                   policy,
		HeartbeatIntervalSeconds: maxInt(*heartbeatInterval, 15),
		SyncIntervalSeconds:      maxInt(*syncInterval, 15),
		InstalledAt:              time.Now().UTC().Format(time.RFC3339),
	}
	if err := saveConfig(cfg, configPathFor(*dataDir)); err != nil {
		return err
	}
	logLocal("info", "agent config saved", nil)

	if err := installOrUpdateService(exePath); err != nil {
		return err
	}
	if err := installScheduledTasks(exePath, policy.ShowTrayStatus); err != nil {
		return err
	}
	if err := sendEnrollment(cfg); err != nil {
		logLocal("warn", "enrollment will retry from service: "+err.Error(), nil)
	}
	_ = runCommand("sc.exe", "start", serviceName)
	fmt.Println("Vulcan Agent installed.")
	return nil
}

func uninstallCommand(args []string) error {
	fs := flag.NewFlagSet("uninstall", flag.ContinueOnError)
	purgeData := fs.Bool("PurgeData", false, "delete ProgramData queue/config/logs")
	if err := fs.Parse(args); err != nil {
		return err
	}
	_ = runCommand("sc.exe", "stop", serviceName)
	time.Sleep(2 * time.Second)
	_ = runCommand("sc.exe", "delete", serviceName)
	_ = runCommand("schtasks.exe", "/Delete", "/TN", "Vulcan Session Collector", "/F")
	_ = runCommand("schtasks.exe", "/Delete", "/TN", "Vulcan Tray", "/F")
	if *purgeData {
		if err := os.RemoveAll(defaultDataDir()); err != nil {
			return err
		}
	}
	fmt.Println("Vulcan Agent uninstalled.")
	return nil
}

func repairCommand(args []string) error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	exePath := filepath.Join(defaultInstallDir(), "VulcanAgent.exe")
	if _, err := os.Stat(exePath); err != nil {
		return fmt.Errorf("installed executable not found at %s: %w", exePath, err)
	}
	if err := installOrUpdateService(exePath); err != nil {
		return err
	}
	if err := installScheduledTasks(exePath, cfg.Policy.ShowTrayStatus); err != nil {
		return err
	}
	if err := sendEnrollment(cfg); err != nil {
		logLocal("warn", "repair enrollment failed: "+err.Error(), nil)
	}
	_ = runCommand("sc.exe", "start", serviceName)
	fmt.Println("Vulcan Agent repaired.")
	return nil
}

func statusCommand(args []string) error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	depth := queueDepth(defaultQueuePath())
	fmt.Printf("Vulcan Agent %s\n", version)
	fmt.Printf("Tenant: %s\n", cfg.TenantID)
	fmt.Printf("Backend: %s\n", cfg.BackendURL)
	fmt.Printf("DeviceId: %s\n", cfg.DeviceID)
	fmt.Printf("MachineFingerprint: %s\n", cfg.MachineFingerprint)
	fmt.Printf("LinkedUser: %s\n", cfg.LinkedUser)
	fmt.Printf("RoleLevel: %s\n", cfg.RoleLevel)
	fmt.Printf("Department: %s\n", cfg.Department)
	fmt.Printf("CollectWindowTitle: %t\n", effectivePolicy(cfg).CollectWindowTitle)
	fmt.Printf("CollectIdleTime: %t\n", effectivePolicy(cfg).CollectIdleTime)
	fmt.Printf("CollectBrowserDomain: %t\n", effectivePolicy(cfg).CollectBrowserDomain)
	fmt.Printf("CollectBrowserUrl: %t\n", effectivePolicy(cfg).CollectBrowserURL)
	fmt.Printf("CollectBrowserHistory: %t\n", effectivePolicy(cfg).CollectBrowserHistory)
	fmt.Printf("CollectProcessList: %t\n", effectivePolicy(cfg).CollectProcessList)
	fmt.Printf("PrivacyMode: %s\n", effectivePolicy(cfg).PrivacyMode)
	machine, _ := machineHealth(effectivePolicy(cfg))
	machineJSON, _ := json.Marshal(machine)
	fmt.Printf("MachineHealth: %s\n", string(machineJSON))
	fmt.Printf("QueueDepth: %d\n\n", depth)
	output, _ := exec.Command("sc.exe", "query", serviceName).CombinedOutput()
	fmt.Println(strings.TrimSpace(string(output)))
	return nil
}

func serviceCommand() error {
	isWindowsService, err := svc.IsWindowsService()
	if err != nil {
		return err
	}
	if !isWindowsService {
		cfg, err := loadConfig(defaultConfigPath())
		if err != nil {
			return err
		}
		runServiceLoop(context.Background(), cfg)
		return nil
	}
	return svc.Run(serviceName, &agentService{configPath: defaultConfigPath()})
}

func (s *agentService) Execute(args []string, requests <-chan svc.ChangeRequest, changes chan<- svc.Status) (bool, uint32) {
	const accepts = svc.AcceptStop | svc.AcceptShutdown
	changes <- svc.Status{State: svc.StartPending}
	cfg, err := loadConfig(s.configPath)
	if err != nil {
		logLocal("error", "service config load failed: "+err.Error(), nil)
		return false, 1
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		runServiceLoop(ctx, cfg)
	}()
	changes <- svc.Status{State: svc.Running, Accepts: accepts}
	for req := range requests {
		switch req.Cmd {
		case svc.Interrogate:
			changes <- svc.Status{State: svc.Running, Accepts: accepts}
		case svc.Stop, svc.Shutdown:
			changes <- svc.Status{State: svc.StopPending}
			cancel()
			<-done
			return false, 0
		default:
			logLocal("warn", fmt.Sprintf("unsupported service command: %v", req.Cmd), nil)
		}
	}
	return false, 0
}

func runServiceLoop(ctx context.Context, cfg Config) {
	logLocal("info", "service loop started", map[string]interface{}{"version": version})
	_ = sendEnrollment(cfg)
	policy := effectivePolicy(cfg)
	heartbeatTicker := time.NewTicker(time.Duration(maxInt(policy.HeartbeatIntervalSeconds, 60)) * time.Second)
	syncTicker := time.NewTicker(time.Duration(maxInt(policy.SyncIntervalSeconds, 30)) * time.Second)
	defer heartbeatTicker.Stop()
	defer syncTicker.Stop()

	var lastErr string
	for {
		select {
		case <-ctx.Done():
			machine, _ := machineHealth(policy)
			_ = sendHeartbeat(cfg, "offline", queueDepth(defaultQueuePath()), "", map[string]interface{}{"collectionQuality": "high", "machine": machine})
			logLocal("info", "service loop stopped", nil)
			return
		case <-heartbeatTicker.C:
			machine, _ := machineHealth(policy)
			if err := sendHeartbeat(cfg, "online", queueDepth(defaultQueuePath()), lastErr, map[string]interface{}{
				"collectionQuality": "high",
				"collectionMethod":  "win32-foreground-window",
				"agentMemoryMb":     agentMemoryMb(),
				"machine":           machine,
				"policy": map[string]interface{}{
					"collectWindowTitle":    policy.CollectWindowTitle,
					"collectIdleTime":       policy.CollectIdleTime,
					"collectBrowserDomain":  policy.CollectBrowserDomain,
					"collectBrowserUrl":     policy.CollectBrowserURL,
					"collectBrowserHistory": policy.CollectBrowserHistory,
					"collectProcessList":    policy.CollectProcessList,
					"privacyMode":           policy.PrivacyMode,
				},
			}); err != nil {
				lastErr = err.Error()
				logLocal("warn", "heartbeat failed: "+lastErr, nil)
			} else {
				lastErr = ""
			}
		case <-syncTicker.C:
			if err := syncQueuedEvents(cfg); err != nil {
				lastErr = err.Error()
				logLocal("warn", "sync failed: "+lastErr, nil)
			} else {
				lastErr = ""
			}
		}
	}
}

func collectorCommand() error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	return collectForegroundLoop(context.Background(), cfg)
}

func trayCommand() error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	logLocal("info", "tray placeholder started", map[string]interface{}{"tenantId": cfg.TenantID, "linkedUser": cfg.LinkedUser})
	for {
		time.Sleep(30 * time.Minute)
	}
}

func runForegroundCollector() error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	return collectForegroundLoop(context.Background(), cfg)
}

func enrollCommand() error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	return sendEnrollment(cfg)
}

func heartbeatCommand() error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	policy := effectivePolicy(cfg)
	machine, _ := machineHealth(policy)
	return sendHeartbeat(cfg, "online", queueDepth(defaultQueuePath()), "", map[string]interface{}{"collectionQuality": "high", "collectionMethod": "manual", "machine": machine})
}

func syncCommand() error {
	cfg, err := loadConfig(defaultConfigPath())
	if err != nil {
		return err
	}
	return syncQueuedEvents(cfg)
}

func collectForegroundLoop(ctx context.Context, cfg Config) error {
	policy := effectivePolicy(cfg)
	logLocal("info", "session collector started", map[string]interface{}{"collectWindowTitle": policy.CollectWindowTitle})
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	var lastApp, lastTitle string
	startedAt := time.Now().UTC()
	var idleStartedAt time.Time
	wasIdle := false
	lastBrowserHistory := time.Time{}

	record := func(endedAt time.Time, eventType string, metadata map[string]interface{}) {
		if lastApp == "" {
			return
		}
		duration := int64(endedAt.Sub(startedAt).Seconds())
		if duration < 1 && eventType != "context_switch" {
			return
		}
		browserDomain, browserURL, adultSignal := normalizeBrowserURL(lastTitle, policy.CollectBrowserURL, policy.CollectBrowserDomain)
		eventMetadata := map[string]interface{}{
			"collector": "windows-session",
			"quality":   "high",
			"method":    "win32-foreground-window",
			"privacy": map[string]interface{}{
				"keystrokes":  false,
				"screenshots": false,
				"clipboard":   false,
				"audio":       false,
				"webcam":      false,
			},
		}
		if browserDomain != "" {
			eventMetadata["browserDomain"] = browserDomain
		}
		if browserURL != "" {
			eventMetadata["browserUrl"] = browserURL
			eventMetadata["urlQueryCollected"] = false
			eventMetadata["urlFragmentCollected"] = false
		}
		if adultSignal {
			eventMetadata["adultContentSignal"] = true
		}
		event := AgentEvent{
			EventID:         uuidV4(),
			EventType:       eventType,
			AppName:         lastApp,
			WindowTitle:     sanitizeTitle(lastTitle, policy.CollectWindowTitle),
			Category:        appCategory(lastApp),
			StartedAt:       startedAt.Format(time.RFC3339),
			EndedAt:         endedAt.Format(time.RFC3339),
			DurationSeconds: duration,
			OSUser:          cfg.OSUser,
			Metadata:        eventMetadata,
		}
		for key, value := range metadata {
			event.Metadata[key] = value
		}
		if err := appendEvent(defaultQueuePath(), event); err != nil {
			logLocal("error", "failed to queue event: "+err.Error(), nil)
		}
	}

	for {
		select {
		case <-ctx.Done():
			record(time.Now().UTC(), "app_focus_ended", nil)
			logLocal("info", "session collector stopped", nil)
			return nil
		case <-ticker.C:
			now := time.Now().UTC()
			if policy.CollectBrowserHistory && (lastBrowserHistory.IsZero() || now.Sub(lastBrowserHistory) >= time.Duration(policy.BrowserHistoryInterval)*time.Second) {
				events, err := collectBrowserHistoryEvents(cfg, policy, now)
				if err != nil {
					logLocal("warn", "browser history collection failed: "+err.Error(), nil)
				}
				for _, event := range events {
					if err := appendEvent(defaultQueuePath(), event); err != nil {
						logLocal("error", "failed to queue browser event: "+err.Error(), nil)
					}
				}
				lastBrowserHistory = now
			}
			if policy.CollectIdleTime {
				idle := idleSeconds()
				isIdle := idle >= int64(policy.IdleThresholdSeconds)
				if isIdle && !wasIdle {
					idleStartedAt = now
					_ = appendEvent(defaultQueuePath(), AgentEvent{
						EventID:         uuidV4(),
						EventType:       "idle_started",
						AppName:         "Sistema",
						Category:        "sistema",
						StartedAt:       now.Format(time.RFC3339),
						EndedAt:         now.Format(time.RFC3339),
						DurationSeconds: 0,
						OSUser:          cfg.OSUser,
						Metadata:        map[string]interface{}{"collector": "windows-session", "idleSeconds": idle, "quality": "high"},
					})
				}
				if !isIdle && wasIdle && !idleStartedAt.IsZero() {
					_ = appendEvent(defaultQueuePath(), AgentEvent{
						EventID:         uuidV4(),
						EventType:       "idle_ended",
						AppName:         "Sistema",
						Category:        "sistema",
						StartedAt:       idleStartedAt.Format(time.RFC3339),
						EndedAt:         now.Format(time.RFC3339),
						DurationSeconds: int64(now.Sub(idleStartedAt).Seconds()),
						OSUser:          cfg.OSUser,
						Metadata:        map[string]interface{}{"collector": "windows-session", "quality": "high"},
					})
				}
				wasIdle = isIdle
			}
			app, title, err := activeForeground()
			if err != nil {
				logLocal("warn", "foreground detection failed: "+err.Error(), nil)
				continue
			}
			if app == "" {
				continue
			}
			title = sanitizeTitle(title, policy.CollectWindowTitle)
			if lastApp == "" {
				lastApp, lastTitle, startedAt = app, title, now
				continue
			}
			if app != lastApp || title != lastTitle {
				record(now, "app_focus_ended", nil)
				_ = appendEvent(defaultQueuePath(), AgentEvent{
					EventID:         uuidV4(),
					EventType:       "context_switch",
					AppName:         "Troca de contexto",
					Category:        "sistema",
					StartedAt:       now.Format(time.RFC3339),
					EndedAt:         now.Format(time.RFC3339),
					DurationSeconds: 0,
					OSUser:          cfg.OSUser,
					Metadata:        map[string]interface{}{"fromApp": lastApp, "toApp": app, "quality": "high"},
				})
				lastApp, lastTitle, startedAt = app, title, now
			}
		}
	}
}

var (
	user32                       = syscall.NewLazyDLL("user32.dll")
	procGetForegroundWindow      = user32.NewProc("GetForegroundWindow")
	procGetWindowTextW           = user32.NewProc("GetWindowTextW")
	procGetWindowTextLengthW     = user32.NewProc("GetWindowTextLengthW")
	procGetWindowThreadProcessID = user32.NewProc("GetWindowThreadProcessId")
	procGetLastInputInfo         = user32.NewProc("GetLastInputInfo")
	kernel32                     = syscall.NewLazyDLL("kernel32.dll")
	procGetTickCount64           = kernel32.NewProc("GetTickCount64")
)

type lastInputInfo struct {
	CbSize uint32
	DwTime uint32
}

func activeForeground() (string, string, error) {
	hwnd, _, _ := procGetForegroundWindow.Call()
	if hwnd == 0 {
		return "", "", nil
	}
	length, _, _ := procGetWindowTextLengthW.Call(hwnd)
	title := ""
	if length > 0 {
		buffer := make([]uint16, length+1)
		procGetWindowTextW.Call(hwnd, uintptr(unsafe.Pointer(&buffer[0])), uintptr(len(buffer)))
		title = windows.UTF16ToString(buffer)
	}
	var pid uint32
	procGetWindowThreadProcessID.Call(hwnd, uintptr(unsafe.Pointer(&pid)))
	app := processName(pid)
	if app == "" {
		app = "UnknownApp"
	}
	return app, title, nil
}

func processName(pid uint32) string {
	handle, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, pid)
	if err != nil {
		return ""
	}
	defer windows.CloseHandle(handle)
	buffer := make([]uint16, windows.MAX_PATH)
	size := uint32(len(buffer))
	if err := windows.QueryFullProcessImageName(handle, 0, &buffer[0], &size); err != nil {
		return ""
	}
	return filepath.Base(windows.UTF16ToString(buffer[:size]))
}

func idleSeconds() int64 {
	info := lastInputInfo{CbSize: uint32(unsafe.Sizeof(lastInputInfo{}))}
	ret, _, _ := procGetLastInputInfo.Call(uintptr(unsafe.Pointer(&info)))
	if ret == 0 {
		return 0
	}
	tick, _, _ := procGetTickCount64.Call()
	if tick == 0 || uint64(info.DwTime) > uint64(tick) {
		return 0
	}
	return int64((uint64(tick) - uint64(info.DwTime)) / 1000)
}

func collectBrowserHistoryEvents(cfg Config, policy AgentPolicy, now time.Time) ([]AgentEvent, error) {
	if !policy.CollectBrowserHistory || (!policy.CollectBrowserDomain && !policy.CollectBrowserURL) {
		return nil, nil
	}
	lookback := maxInt(policy.BrowserHistoryLookback, 60)
	maxEvents := maxInt(policy.BrowserHistoryMaxEvents, 50)
	if maxEvents > 250 {
		maxEvents = 250
	}
	since := now.Add(-time.Duration(lookback) * time.Minute)
	state := readBrowserHistoryState()
	seen := map[string]bool{}
	for _, key := range state.Seen {
		seen[key] = true
	}
	var events []AgentEvent
	for _, profile := range browserProfiles() {
		remaining := maxEvents - len(events)
		if remaining <= 0 {
			break
		}
		var visits []browserVisit
		var err error
		if profile.Engine == "chromium" {
			visits, err = fetchChromiumHistory(profile, since, remaining*3)
		} else {
			visits, err = fetchFirefoxHistory(profile, since, remaining*3)
		}
		if err != nil {
			logLocal("warn", "browser history read failed: "+err.Error(), map[string]interface{}{"browser": profile.Browser, "profile": profile.Profile})
			continue
		}
		for _, visit := range visits {
			domain, safeURL, adultSignal := normalizeBrowserURL(visit.URL, policy.CollectBrowserURL, policy.CollectBrowserDomain)
			if domain == "" && safeURL == "" {
				continue
			}
			key := browserVisitKey(profile.Browser, profile.Profile, visit.VisitedAt, safeURL, domain)
			if seen[key] {
				continue
			}
			title := sanitizeTitle(visit.Title, policy.CollectBrowserPageTitle && policy.CollectWindowTitle)
			event := AgentEvent{
				EventID:         uuidV4(),
				EventType:       "browser_history_visit",
				AppName:         profile.Browser,
				WindowTitle:     title,
				Category:        map[bool]string{true: "navegador_adulto", false: "navegador"}[adultSignal],
				StartedAt:       visit.VisitedAt.Format(time.RFC3339),
				EndedAt:         visit.VisitedAt.Format(time.RFC3339),
				DurationSeconds: 0,
				OSUser:          cfg.OSUser,
				Metadata: map[string]interface{}{
					"collector":              "windows-browser-history",
					"quality":                "high",
					"method":                 profile.Engine + "-history",
					"browser":                profile.Browser,
					"browserProfile":         profile.Profile,
					"browserDomain":          domain,
					"browserUrl":             safeURL,
					"adultContentSignal":     adultSignal,
					"urlQueryCollected":      false,
					"urlFragmentCollected":   false,
					"historyLookbackMinutes": lookback,
					"privacy": map[string]interface{}{
						"keystrokes":  false,
						"screenshots": false,
						"clipboard":   false,
						"audio":       false,
						"webcam":      false,
						"cookies":     false,
						"tokens":      false,
					},
				},
			}
			events = append(events, event)
			seen[key] = true
			if len(events) >= maxEvents {
				break
			}
		}
	}
	if len(events) > 0 {
		state.Seen = keysFromSeen(seen, 10000)
		state.LastCollectedAt = now.Format(time.RFC3339)
		_ = saveBrowserHistoryState(state)
		logLocal("info", "browser history collected", map[string]interface{}{"events": len(events)})
	}
	return events, nil
}

func browserProfiles() []browserProfile {
	localAppData := os.Getenv("LOCALAPPDATA")
	appData := os.Getenv("APPDATA")
	var profiles []browserProfile
	chromiumRoots := []struct {
		browser string
		root    string
	}{
		{"Google Chrome", filepath.Join(localAppData, "Google", "Chrome", "User Data")},
		{"Microsoft Edge", filepath.Join(localAppData, "Microsoft", "Edge", "User Data")},
		{"Brave", filepath.Join(localAppData, "BraveSoftware", "Brave-Browser", "User Data")},
		{"Chromium", filepath.Join(localAppData, "Chromium", "User Data")},
	}
	for _, item := range chromiumRoots {
		if item.root == "" {
			continue
		}
		matches, _ := filepath.Glob(filepath.Join(item.root, "*", "History"))
		for _, path := range matches {
			profile := filepath.Base(filepath.Dir(path))
			if strings.EqualFold(profile, "Crashpad") || strings.EqualFold(profile, "ShaderCache") {
				continue
			}
			profiles = append(profiles, browserProfile{Browser: item.browser, Engine: "chromium", Profile: profile, Path: path})
		}
	}
	if appData != "" {
		matches, _ := filepath.Glob(filepath.Join(appData, "Mozilla", "Firefox", "Profiles", "*", "places.sqlite"))
		for _, path := range matches {
			profiles = append(profiles, browserProfile{Browser: "Firefox", Engine: "firefox", Profile: filepath.Base(filepath.Dir(path)), Path: path})
		}
	}
	return profiles
}

func fetchChromiumHistory(profile browserProfile, since time.Time, limit int) ([]browserVisit, error) {
	copied, cleanup, err := copySQLiteDatabase(profile.Path)
	if err != nil {
		return nil, err
	}
	defer cleanup()
	db, err := sql.Open("sqlite", copied)
	if err != nil {
		return nil, err
	}
	defer db.Close()
	threshold := (since.Unix() + windowsEpochOffsetSeconds) * 1000000
	rows, err := db.Query(`
		select urls.url, coalesce(urls.title, ''), visits.visit_time
		from visits
		join urls on urls.id = visits.url
		where visits.visit_time >= ?
		order by visits.visit_time desc
		limit ?`, threshold, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var visits []browserVisit
	for rows.Next() {
		var rawURL, title string
		var visitedRaw int64
		if err := rows.Scan(&rawURL, &title, &visitedRaw); err != nil {
			continue
		}
		visits = append(visits, browserVisit{URL: rawURL, Title: title, VisitedAt: chromeTimeToTime(visitedRaw)})
	}
	return visits, rows.Err()
}

func fetchFirefoxHistory(profile browserProfile, since time.Time, limit int) ([]browserVisit, error) {
	copied, cleanup, err := copySQLiteDatabase(profile.Path)
	if err != nil {
		return nil, err
	}
	defer cleanup()
	db, err := sql.Open("sqlite", copied)
	if err != nil {
		return nil, err
	}
	defer db.Close()
	threshold := since.Unix() * 1000000
	rows, err := db.Query(`
		select moz_places.url, coalesce(moz_places.title, ''), moz_historyvisits.visit_date
		from moz_historyvisits
		join moz_places on moz_places.id = moz_historyvisits.place_id
		where moz_historyvisits.visit_date >= ?
		order by moz_historyvisits.visit_date desc
		limit ?`, threshold, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var visits []browserVisit
	for rows.Next() {
		var rawURL, title string
		var visitedRaw int64
		if err := rows.Scan(&rawURL, &title, &visitedRaw); err != nil {
			continue
		}
		visits = append(visits, browserVisit{URL: rawURL, Title: title, VisitedAt: time.UnixMicro(visitedRaw).UTC()})
	}
	return visits, rows.Err()
}

func copySQLiteDatabase(source string) (string, func(), error) {
	if source == "" {
		return "", func() {}, errors.New("empty sqlite source")
	}
	tmp, err := os.CreateTemp("", "vulcan-browser-*.sqlite")
	if err != nil {
		return "", func() {}, err
	}
	tmpPath := tmp.Name()
	_ = tmp.Close()
	if err := copyFile(source, tmpPath); err != nil {
		_ = os.Remove(tmpPath)
		return "", func() {}, err
	}
	return tmpPath, func() { _ = os.Remove(tmpPath) }, nil
}

func chromeTimeToTime(value int64) time.Time {
	seconds := (value / 1000000) - windowsEpochOffsetSeconds
	micros := value % 1000000
	return time.Unix(seconds, micros*1000).UTC()
}

func normalizeBrowserURL(raw string, collectURL bool, collectDomain bool) (string, string, bool) {
	if raw == "" || (!collectURL && !collectDomain) {
		return "", "", false
	}
	raw = strings.TrimSpace(raw)
	if !strings.HasPrefix(strings.ToLower(raw), "http://") && !strings.HasPrefix(strings.ToLower(raw), "https://") {
		if index := strings.Index(strings.ToLower(raw), "https://"); index >= 0 {
			raw = raw[index:]
		} else if index := strings.Index(strings.ToLower(raw), "http://"); index >= 0 {
			raw = raw[index:]
		} else {
			return "", "", false
		}
	}
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Host == "" || (parsed.Scheme != "http" && parsed.Scheme != "https") {
		return "", "", false
	}
	domain := strings.ToLower(parsed.Hostname())
	if domain == "" {
		return "", "", false
	}
	adultSignal := isAdultDomain(domain)
	path := parsed.EscapedPath()
	if containsSensitive(path) {
		path = "/"
	}
	safeURL := ""
	if collectURL {
		safeURL = parsed.Scheme + "://" + domain + path
		if len(safeURL) > 500 {
			safeURL = safeURL[:500]
		}
	}
	if !collectDomain {
		domain = ""
	}
	return domain, safeURL, adultSignal
}

func containsSensitive(value string) bool {
	lower := strings.ToLower(value)
	for _, pattern := range sensitivePatterns {
		if strings.Contains(lower, pattern) {
			return true
		}
	}
	return false
}

func isAdultDomain(domain string) bool {
	normalized := strings.TrimPrefix(strings.ToLower(domain), "www.")
	for _, pattern := range adultDomainPatterns {
		if strings.Contains(normalized, pattern) {
			return true
		}
	}
	return false
}

func browserVisitKey(browser string, profile string, visitedAt time.Time, safeURL string, domain string) string {
	sum := sha256.Sum256([]byte(strings.Join([]string{browser, profile, visitedAt.Format(time.RFC3339Nano), safeURL, domain}, "|")))
	return hex.EncodeToString(sum[:])
}

func browserHistoryStatePath() string {
	return filepath.Join(defaultDataDir(), "browser-history-state.json")
}

func readBrowserHistoryState() browserHistoryState {
	data, err := os.ReadFile(browserHistoryStatePath())
	if err != nil {
		return browserHistoryState{}
	}
	var state browserHistoryState
	if err := json.Unmarshal(data, &state); err != nil {
		return browserHistoryState{}
	}
	return state
}

func saveBrowserHistoryState(state browserHistoryState) error {
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(browserHistoryStatePath(), data, 0640)
}

func keysFromSeen(seen map[string]bool, max int) []string {
	keys := make([]string, 0, len(seen))
	for key := range seen {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	if len(keys) > max {
		keys = keys[len(keys)-max:]
	}
	return keys
}

func sendEnrollment(cfg Config) error {
	req := enrollRequest{
		TenantID:            cfg.TenantID,
		EnrollmentToken:     cfg.EnrollmentToken,
		Hostname:            cfg.Hostname,
		OSUser:              cfg.OSUser,
		OSVersion:           cfg.OSVersion,
		DeviceID:            cfg.DeviceID,
		MachineFingerprint:  cfg.MachineFingerprint,
		AgentVersion:        version,
		LinkedUser:          cfg.LinkedUser,
		UserID:              cfg.UserID,
		MembershipID:        cfg.MembershipID,
		RoleLevel:           cfg.RoleLevel,
		Department:          cfg.Department,
		ManagerMembershipID: cfg.ManagerMembershipID,
		Note:                cfg.Note,
	}
	var res enrollResponse
	if err := postJSON(cfg.BackendURL+"/agent/enroll", req, &res); err != nil {
		return err
	}
	if !res.Accepted {
		return errors.New("backend rejected enrollment")
	}
	if res.DeviceID != "" && res.DeviceID != cfg.DeviceID {
		cfg.DeviceID = res.DeviceID
		if res.HeartbeatIntervalSeconds > 0 {
			cfg.HeartbeatIntervalSeconds = res.HeartbeatIntervalSeconds
		}
		if res.SyncIntervalSeconds > 0 {
			cfg.SyncIntervalSeconds = res.SyncIntervalSeconds
		}
		if err := saveConfig(cfg, defaultConfigPath()); err != nil {
			return err
		}
	}
	logLocal("info", "agent enrolled", map[string]interface{}{"deviceId": cfg.DeviceID})
	return nil
}

func sendHeartbeat(cfg Config, status string, depth int, lastErr string, metadata map[string]interface{}) error {
	mergedMetadata := identityMetadata(cfg)
	for key, value := range metadata {
		mergedMetadata[key] = value
	}
	req := heartbeatRequest{
		TenantID:           cfg.TenantID,
		EnrollmentToken:    cfg.EnrollmentToken,
		DeviceID:           cfg.DeviceID,
		MachineFingerprint: cfg.MachineFingerprint,
		Hostname:           cfg.Hostname,
		AgentVersion:       version,
		Status:             status,
		QueueDepth:         depth,
		LastError:          lastErr,
		Metadata:           mergedMetadata,
	}
	return postJSON(cfg.BackendURL+"/agent/heartbeat", req, &map[string]interface{}{})
}

func syncQueuedEvents(cfg Config) error {
	events, err := readEvents(defaultQueuePath(), 100)
	if err != nil {
		return err
	}
	if len(events) == 0 {
		return nil
	}
	req := syncRequest{
		TenantID:           cfg.TenantID,
		EnrollmentToken:    cfg.EnrollmentToken,
		DeviceID:           cfg.DeviceID,
		MembershipID:       cfg.MembershipID,
		MachineFingerprint: cfg.MachineFingerprint,
		Hostname:           cfg.Hostname,
		Events:             events,
	}
	var res syncResponse
	if err := postJSON(cfg.BackendURL+"/agent/sync", req, &res); err != nil {
		return err
	}
	if !res.Accepted {
		return errors.New("backend rejected event sync")
	}
	stored := res.Stored
	if stored <= 0 {
		stored = len(events)
	}
	if err := dropEvents(defaultQueuePath(), stored); err != nil {
		return err
	}
	logLocal("info", "events synced", map[string]interface{}{"stored": stored})
	return nil
}

func postJSON(url string, request interface{}, response interface{}) error {
	body, err := json.Marshal(request)
	if err != nil {
		return err
	}
	client := &http.Client{Timeout: 30 * time.Second}
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "VulcanAgent/"+version)
	res, err := client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	payload, _ := io.ReadAll(io.LimitReader(res.Body, 1<<20))
	if res.StatusCode < 200 || res.StatusCode > 299 {
		return fmt.Errorf("backend returned %s: %s", res.Status, strings.TrimSpace(string(payload)))
	}
	if response != nil && len(payload) > 0 {
		if err := json.Unmarshal(payload, response); err != nil {
			return err
		}
	}
	return nil
}

func appendEvent(path string, event AgentEvent) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0640)
	if err != nil {
		return err
	}
	defer file.Close()
	line, err := json.Marshal(event)
	if err != nil {
		return err
	}
	if _, err := file.Write(append(line, '\n')); err != nil {
		return err
	}
	return nil
}

func readEvents(path string, max int) ([]AgentEvent, error) {
	file, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var events []AgentEvent
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if len(events) >= max {
			break
		}
		var event AgentEvent
		if err := json.Unmarshal(scanner.Bytes(), &event); err == nil && event.AppName != "" {
			events = append(events, event)
		}
	}
	return events, scanner.Err()
}

func dropEvents(path string, count int) error {
	file, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	defer file.Close()
	tmpPath := path + ".tmp"
	tmp, err := os.Create(tmpPath)
	if err != nil {
		return err
	}
	defer tmp.Close()
	scanner := bufio.NewScanner(file)
	index := 0
	for scanner.Scan() {
		if index >= count {
			if _, err := tmp.Write(append(scanner.Bytes(), '\n')); err != nil {
				return err
			}
		}
		index++
	}
	if err := scanner.Err(); err != nil {
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}
	return os.Rename(tmpPath, path)
}

func queueDepth(path string) int {
	file, err := os.Open(path)
	if err != nil {
		return 0
	}
	defer file.Close()
	count := 0
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		count++
	}
	return count
}

func installOrUpdateService(exePath string) error {
	binPath := fmt.Sprintf(`"%s" service`, exePath)
	if err := runCommand("sc.exe", "create", serviceName, "binPath=", binPath, "start=", "auto", "DisplayName=", displayName); err != nil {
		if err := runCommand("sc.exe", "config", serviceName, "binPath=", binPath, "start=", "auto", "DisplayName=", displayName); err != nil {
			return err
		}
	}
	_ = runCommand("sc.exe", "description", serviceName, "Vulcan operational intelligence agent. No keystrokes, screenshots, audio or webcam collection.")
	_ = runCommand("sc.exe", "failure", serviceName, "reset=", "60", "actions=", "restart/60000/restart/60000/restart/120000")
	_ = runCommand("sc.exe", "failureflag", serviceName, "1")
	return nil
}

func installScheduledTasks(exePath string, showTrayStatus bool) error {
	collectorCmd := fmt.Sprintf(`"%s" collector`, exePath)
	if err := runCommand("schtasks.exe", "/Create", "/TN", "Vulcan Session Collector", "/SC", "ONLOGON", "/TR", collectorCmd, "/RL", "LIMITED", "/F"); err != nil {
		return err
	}
	if showTrayStatus {
		trayCmd := fmt.Sprintf(`"%s" tray`, exePath)
		_ = runCommand("schtasks.exe", "/Create", "/TN", "Vulcan Tray", "/SC", "ONLOGON", "/TR", trayCmd, "/RL", "LIMITED", "/F")
	} else {
		_ = runCommand("schtasks.exe", "/Delete", "/TN", "Vulcan Tray", "/F")
	}
	return nil
}

func runCommand(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("%s %s failed: %w: %s", name, strings.Join(args, " "), err, strings.TrimSpace(string(output)))
	}
	return nil
}

func copyInstallBinaries(installDir string) (string, error) {
	serviceDestination := filepath.Join(installDir, "VulcanAgent.exe")
	controlDestination := filepath.Join(installDir, "VulcanAgentCtl.exe")
	self, err := os.Executable()
	if err != nil {
		return "", err
	}
	siblingService := filepath.Join(filepath.Dir(self), "VulcanAgent.exe")
	if _, err := os.Stat(siblingService); err == nil && !strings.EqualFold(self, siblingService) {
		if err := copyFile(siblingService, serviceDestination); err != nil {
			return "", err
		}
	} else if err := copyFile(self, serviceDestination); err != nil {
		return "", err
	}
	if err := copyFile(self, controlDestination); err != nil {
		return "", err
	}
	return serviceDestination, nil
}

func copySelf(destination string) error {
	source, err := os.Executable()
	if err != nil {
		return err
	}
	return copyFile(source, destination)
}

func copyFile(source string, destination string) error {
	sourceAbs, _ := filepath.Abs(source)
	destAbs, _ := filepath.Abs(destination)
	if strings.EqualFold(sourceAbs, destAbs) {
		return nil
	}
	input, err := os.Open(source)
	if err != nil {
		return err
	}
	defer input.Close()
	output, err := os.Create(destination)
	if err != nil {
		return err
	}
	if _, err := io.Copy(output, input); err != nil {
		_ = output.Close()
		return err
	}
	return output.Close()
}

func ensureAgentDirs(dataDir string) error {
	for _, dir := range []string{
		filepath.Join(dataDir, "config"),
		filepath.Join(dataDir, "queue"),
		filepath.Join(dataDir, "logs"),
	} {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return err
		}
	}
	return nil
}

func saveConfig(cfg Config, path string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0640)
}

func loadConfig(path string) (Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, err
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, err
	}
	if cfg.BackendURL == "" || cfg.TenantID == "" || cfg.EnrollmentToken == "" {
		return Config{}, errors.New("agent config is incomplete")
	}
	cfg.BackendURL = strings.TrimRight(cfg.BackendURL, "/")
	return cfg, nil
}

func logLocal(level string, message string, metadata map[string]interface{}) {
	path := filepath.Join(defaultDataDir(), "logs", "agent.log")
	_ = os.MkdirAll(filepath.Dir(path), 0755)
	if info, err := os.Stat(path); err == nil && info.Size() > 5*1024*1024 {
		_ = os.Rename(path, path+".1")
	}
	entry := logEntry{
		Level:     level,
		Message:   message,
		CreatedAt: time.Now().UTC().Format(time.RFC3339),
		Metadata:  metadata,
	}
	line, _ := json.Marshal(entry)
	file, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0640)
	if err != nil {
		return
	}
	defer file.Close()
	_, _ = file.Write(append(line, '\n'))
}

func sanitizeTitle(title string, collect bool) string {
	if !collect || title == "" {
		return ""
	}
	lower := strings.ToLower(title)
	redactPatterns := []string{
		"password", "senha", "secret", "token", "login", "log in", "sign in",
		"whatsapp", "telegram", "signal", "bank", "banco", "cpf", "cartao", "card",
		"private", "privado", "confidential", "confidencial",
	}
	for _, pattern := range redactPatterns {
		if strings.Contains(lower, pattern) {
			return "[redacted]"
		}
	}
	if len(title) > 180 {
		return title[:180]
	}
	return title
}

func appCategory(app string) string {
	lower := strings.ToLower(app)
	categories := map[string][]string{
		"navegador":       {"chrome", "chromium", "firefox", "brave", "edge", "opera", "vivaldi"},
		"comunicação":     {"slack", "teams", "discord", "zoom", "telegram", "whatsapp"},
		"desenvolvimento": {"code", "vscode", "cursor", "devenv", "visualstudio", "terminal", "powershell"},
		"documentos":      {"winword", "excel", "powerpnt", "onenote", "libreoffice"},
		"erp/crm":         {"erp", "sap", "totvs", "crm", "salesforce"},
		"sistema":         {"explorer", "dwm", "systemsettings"},
	}
	for category, terms := range categories {
		for _, term := range terms {
			if strings.Contains(lower, term) {
				return category
			}
		}
	}
	return "operacional"
}

func localIP() string {
	conn, err := net.DialTimeout("udp", "1.1.1.1:80", 2*time.Second)
	if err != nil {
		return ""
	}
	defer conn.Close()
	if addr, ok := conn.LocalAddr().(*net.UDPAddr); ok {
		return addr.IP.String()
	}
	return ""
}

func localIPs() []string {
	var values []string
	interfaces, err := net.Interfaces()
	if err != nil {
		return values
	}
	for _, item := range interfaces {
		if item.Flags&net.FlagUp == 0 || item.Flags&net.FlagLoopback != 0 {
			continue
		}
		addrs, err := item.Addrs()
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			var ip net.IP
			switch value := addr.(type) {
			case *net.IPNet:
				ip = value.IP
			case *net.IPAddr:
				ip = value.IP
			}
			if ip == nil || ip.IsLoopback() {
				continue
			}
			if ipv4 := ip.To4(); ipv4 != nil {
				values = append(values, ipv4.String())
			}
		}
	}
	sort.Strings(values)
	return values
}

func identityMetadata(cfg Config) map[string]interface{} {
	return map[string]interface{}{
		"hostname":             cfg.Hostname,
		"computerName":         os.Getenv("COMPUTERNAME"),
		"domain":               os.Getenv("USERDOMAIN"),
		"userDnsDomain":        os.Getenv("USERDNSDOMAIN"),
		"osUser":               cfg.OSUser,
		"currentUser":          currentUser(),
		"linkedUser":           cfg.LinkedUser,
		"osVersion":            cfg.OSVersion,
		"localIp":              localIP(),
		"localIps":             localIPs(),
		"agentVersion":         version,
		"roleLevel":            cfg.RoleLevel,
		"department":           cfg.Department,
		"managerMembershipId":  cfg.ManagerMembershipID,
		"installedAt":          cfg.InstalledAt,
		"machineFingerprint":   cfg.MachineFingerprint,
		"windowsSessionSource": "service-heartbeat",
	}
}

func agentMemoryMb() uint64 {
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	return stats.Sys / 1024 / 1024
}

func machineHealth(policy AgentPolicy) (map[string]interface{}, error) {
	health := map[string]interface{}{
		"cpuCount": os.Getenv("NUMBER_OF_PROCESSORS"),
	}
	if runtime.NumCPU() > 0 {
		health["cpuCount"] = runtime.NumCPU()
	}
	for key, value := range memoryHealth() {
		health[key] = value
	}
	for key, value := range diskHealth() {
		health[key] = value
	}
	if policy.CollectProcessList {
		health["topProcesses"] = topProcesses(8)
	}
	return health, nil
}

func memoryHealth() map[string]interface{} {
	type memoryStatusEx struct {
		Length               uint32
		MemoryLoad           uint32
		TotalPhys            uint64
		AvailPhys            uint64
		TotalPageFile        uint64
		AvailPageFile        uint64
		TotalVirtual         uint64
		AvailVirtual         uint64
		AvailExtendedVirtual uint64
	}
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	proc := kernel32.NewProc("GlobalMemoryStatusEx")
	status := memoryStatusEx{Length: uint32(unsafe.Sizeof(memoryStatusEx{}))}
	ret, _, _ := proc.Call(uintptr(unsafe.Pointer(&status)))
	if ret == 0 || status.TotalPhys == 0 {
		return map[string]interface{}{}
	}
	return map[string]interface{}{
		"memoryTotalMb":     status.TotalPhys / 1024 / 1024,
		"memoryAvailableMb": status.AvailPhys / 1024 / 1024,
		"memoryUsedPercent": roundOne(float64(status.MemoryLoad)),
		"pageFileTotalMb":   status.TotalPageFile / 1024 / 1024,
		"pageFileUsedMb":    (status.TotalPageFile - status.AvailPageFile) / 1024 / 1024,
	}
}

func diskHealth() map[string]interface{} {
	root := os.Getenv("SystemDrive")
	if root == "" {
		root = "C:"
	}
	if !strings.HasSuffix(root, `\`) {
		root += `\`
	}
	var freeAvailable, total, free uint64
	err := windows.GetDiskFreeSpaceEx(windows.StringToUTF16Ptr(root), &freeAvailable, &total, &free)
	if err != nil || total == 0 {
		return map[string]interface{}{}
	}
	used := total - free
	return map[string]interface{}{
		"diskPath":        root,
		"diskTotalGb":     roundOne(float64(total) / 1024 / 1024 / 1024),
		"diskFreeGb":      roundOne(float64(free) / 1024 / 1024 / 1024),
		"diskUsedPercent": roundOne(float64(used) * 100 / float64(total)),
	}
}

func topProcesses(limit int) []map[string]interface{} {
	cmd := exec.Command("tasklist.exe", "/FO", "CSV", "/NH")
	output, err := cmd.Output()
	if err != nil {
		return nil
	}
	reader := csv.NewReader(strings.NewReader(string(output)))
	records, err := reader.ReadAll()
	if err != nil {
		return nil
	}
	type processRow struct {
		name string
		mem  int
	}
	var rows []processRow
	for _, record := range records {
		if len(record) < 5 {
			continue
		}
		memRaw := strings.NewReplacer("K", "", ".", "", ",", "", " ", "").Replace(record[4])
		var mem int
		fmt.Sscanf(memRaw, "%d", &mem)
		if record[0] != "" {
			rows = append(rows, processRow{name: record[0], mem: mem})
		}
	}
	sort.Slice(rows, func(i, j int) bool { return rows[i].mem > rows[j].mem })
	if len(rows) > limit {
		rows = rows[:limit]
	}
	result := make([]map[string]interface{}, 0, len(rows))
	for _, row := range rows {
		result = append(result, map[string]interface{}{"name": row.name, "memoryKb": row.mem})
	}
	return result
}

func roundOne(value float64) float64 {
	return float64(int(value*10+0.5)) / 10
}

func defaultInstallDir() string {
	if value := os.Getenv("ProgramFiles"); value != "" {
		return filepath.Join(value, "Vulcan", "Agent")
	}
	return `C:\Program Files\Vulcan\Agent`
}

func defaultDataDir() string {
	if value := os.Getenv("ProgramData"); value != "" {
		return filepath.Join(value, "Vulcan", "Agent")
	}
	return `C:\ProgramData\Vulcan\Agent`
}

func defaultConfigPath() string {
	if value := os.Getenv("VULCAN_AGENT_CONFIG"); value != "" {
		return value
	}
	return configPathFor(defaultDataDir())
}

func configPathFor(dataDir string) string {
	return filepath.Join(dataDir, "config", "agent.json")
}

func defaultQueuePath() string {
	return filepath.Join(defaultDataDir(), "queue", "events.jsonl")
}

func hostname() string {
	value, err := os.Hostname()
	if err == nil && value != "" {
		return value
	}
	return "unknown-host"
}

func currentUser() string {
	if value := os.Getenv("USERNAME"); value != "" {
		if domain := os.Getenv("USERDOMAIN"); domain != "" {
			return domain + `\` + value
		}
		return value
	}
	return os.Getenv("USER")
}

func osVersion() string {
	output, err := exec.Command("cmd.exe", "/C", "ver").CombinedOutput()
	if err == nil && len(output) > 0 {
		return strings.TrimSpace(string(output))
	}
	return runtime.GOOS
}

func machineFingerprint(tenantID string, backendURL string) string {
	source := strings.Join([]string{tenantID, backendURL, hostname(), os.Getenv("COMPUTERNAME"), currentUser()}, "|")
	sum := sha256.Sum256([]byte(source))
	return hex.EncodeToString(sum[:])
}

func uuidV4() string {
	bytes := make([]byte, 16)
	if _, err := rand.Read(bytes); err != nil {
		sum := sha256.Sum256([]byte(fmt.Sprintf("%s-%d", hostname(), time.Now().UnixNano())))
		copy(bytes, sum[:16])
	}
	bytes[6] = (bytes[6] & 0x0f) | 0x40
	bytes[8] = (bytes[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", bytes[0:4], bytes[4:6], bytes[6:8], bytes[8:10], bytes[10:])
}

func maxInt(value int, minimum int) int {
	if value < minimum {
		return minimum
	}
	return value
}

func defaultAgentPolicy(collectWindowTitle bool, syncInterval int, heartbeatInterval int, corporateMonitoring bool) AgentPolicy {
	policy := AgentPolicy{
		CollectAppName:           true,
		CollectWindowTitle:       collectWindowTitle,
		CollectIdleTime:          true,
		CollectSessionEvents:     true,
		CollectBrowserDomain:     false,
		CollectBrowserURL:        false,
		CollectBrowserHistory:    false,
		CollectBrowserPageTitle:  false,
		CollectProcessList:       false,
		CollectSystemMetrics:     true,
		RedactSensitiveTerms:     true,
		BrowserHistoryInterval:   300,
		BrowserHistoryLookback:   60,
		BrowserHistoryMaxEvents:  50,
		SyncIntervalSeconds:      maxInt(syncInterval, 15),
		HeartbeatIntervalSeconds: maxInt(heartbeatInterval, 15),
		OfflineQueueEnabled:      true,
		MaxOfflineQueueSize:      10000,
		AllowUserPause:           true,
		ShowTrayStatus:           true,
		PrivacyMode:              "standard",
		IdleThresholdSeconds:     300,
	}
	if corporateMonitoring {
		policy.CollectWindowTitle = true
		policy.CollectBrowserDomain = true
		policy.CollectBrowserURL = true
		policy.CollectBrowserHistory = true
		policy.CollectBrowserPageTitle = true
		policy.CollectProcessList = true
		policy.AllowUserPause = false
		policy.ShowTrayStatus = false
		policy.PrivacyMode = "corporate"
		policy.BrowserHistoryLookback = 120
		policy.BrowserHistoryMaxEvents = 100
	}
	return policy
}

func effectivePolicy(cfg Config) AgentPolicy {
	policy := cfg.Policy
	if !policy.CollectAppName && policy.PrivacyMode == "" {
		policy = defaultAgentPolicy(cfg.CollectWindowTitle, cfg.SyncIntervalSeconds, cfg.HeartbeatIntervalSeconds, false)
	}
	if cfg.CollectWindowTitle {
		policy.CollectWindowTitle = true
	}
	if policy.SyncIntervalSeconds < 15 {
		policy.SyncIntervalSeconds = maxInt(cfg.SyncIntervalSeconds, 15)
	}
	if policy.HeartbeatIntervalSeconds < 15 {
		policy.HeartbeatIntervalSeconds = maxInt(cfg.HeartbeatIntervalSeconds, 15)
	}
	if policy.MaxOfflineQueueSize < 100 {
		policy.MaxOfflineQueueSize = 10000
	}
	if policy.IdleThresholdSeconds < 30 {
		policy.IdleThresholdSeconds = 300
	}
	if policy.BrowserHistoryInterval < 60 {
		policy.BrowserHistoryInterval = 300
	}
	if policy.BrowserHistoryLookback < 5 {
		policy.BrowserHistoryLookback = 60
	}
	if policy.BrowserHistoryLookback > 1440 {
		policy.BrowserHistoryLookback = 1440
	}
	if policy.BrowserHistoryMaxEvents < 1 {
		policy.BrowserHistoryMaxEvents = 50
	}
	if policy.BrowserHistoryMaxEvents > 250 {
		policy.BrowserHistoryMaxEvents = 250
	}
	return policy
}
