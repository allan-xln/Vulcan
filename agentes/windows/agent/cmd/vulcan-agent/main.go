//go:build windows

package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"
	"unsafe"

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
	CollectProcessList       bool   `json:"collectProcessList"`
	CollectSystemMetrics     bool   `json:"collectSystemMetrics"`
	RedactSensitiveTerms     bool   `json:"redactSensitiveTerms"`
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
		CollectWindowTitle:       *collectWindowTitle,
		Policy:                   defaultAgentPolicy(*collectWindowTitle, maxInt(*syncInterval, 15), maxInt(*heartbeatInterval, 15)),
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
	if err := installScheduledTasks(exePath); err != nil {
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
	if err := installScheduledTasks(exePath); err != nil {
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
	fmt.Printf("CollectProcessList: %t\n", effectivePolicy(cfg).CollectProcessList)
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
			_ = sendHeartbeat(cfg, "offline", queueDepth(defaultQueuePath()), "", map[string]interface{}{"collectionQuality": "high", "localIp": localIP()})
			logLocal("info", "service loop stopped", nil)
			return
		case <-heartbeatTicker.C:
			if err := sendHeartbeat(cfg, "online", queueDepth(defaultQueuePath()), lastErr, map[string]interface{}{
				"collectionQuality": "high",
				"collectionMethod":  "win32-foreground-window",
				"localIp":           localIP(),
				"agentMemoryMb":     agentMemoryMb(),
				"policy": map[string]interface{}{
					"collectWindowTitle": policy.CollectWindowTitle,
					"collectIdleTime":    policy.CollectIdleTime,
					"collectBrowserUrl":  policy.CollectBrowserURL,
					"collectProcessList": policy.CollectProcessList,
					"privacyMode":        policy.PrivacyMode,
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
	return sendHeartbeat(cfg, "online", queueDepth(defaultQueuePath()), "", map[string]interface{}{"collectionQuality": "high", "collectionMethod": "manual"})
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

	record := func(endedAt time.Time, eventType string, metadata map[string]interface{}) {
		if lastApp == "" {
			return
		}
		duration := int64(endedAt.Sub(startedAt).Seconds())
		if duration < 1 && eventType != "context_switch" {
			return
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
			Metadata: map[string]interface{}{
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
			},
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
		Metadata:           metadata,
	}
	return postJSON(cfg.BackendURL+"/agent/heartbeat", req, &map[string]interface{}{})
}

func syncQueuedEvents(cfg Config) error {
	events, err := readEvents(defaultQueuePath(), 200)
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
	client := &http.Client{Timeout: 20 * time.Second}
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

func installScheduledTasks(exePath string) error {
	collectorCmd := fmt.Sprintf(`"%s" collector`, exePath)
	trayCmd := fmt.Sprintf(`"%s" tray`, exePath)
	if err := runCommand("schtasks.exe", "/Create", "/TN", "Vulcan Session Collector", "/SC", "ONLOGON", "/TR", collectorCmd, "/RL", "LIMITED", "/F"); err != nil {
		return err
	}
	_ = runCommand("schtasks.exe", "/Create", "/TN", "Vulcan Tray", "/SC", "ONLOGON", "/TR", trayCmd, "/RL", "LIMITED", "/F")
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

func agentMemoryMb() uint64 {
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	return stats.Sys / 1024 / 1024
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

func defaultAgentPolicy(collectWindowTitle bool, syncInterval int, heartbeatInterval int) AgentPolicy {
	return AgentPolicy{
		CollectAppName:           true,
		CollectWindowTitle:       collectWindowTitle,
		CollectIdleTime:          true,
		CollectSessionEvents:     true,
		CollectBrowserDomain:     false,
		CollectBrowserURL:        false,
		CollectProcessList:       false,
		CollectSystemMetrics:     true,
		RedactSensitiveTerms:     true,
		SyncIntervalSeconds:      maxInt(syncInterval, 15),
		HeartbeatIntervalSeconds: maxInt(heartbeatInterval, 15),
		OfflineQueueEnabled:      true,
		MaxOfflineQueueSize:      10000,
		AllowUserPause:           true,
		ShowTrayStatus:           true,
		PrivacyMode:              "standard",
		IdleThresholdSeconds:     300,
	}
}

func effectivePolicy(cfg Config) AgentPolicy {
	policy := cfg.Policy
	if !policy.CollectAppName && policy.PrivacyMode == "" {
		policy = defaultAgentPolicy(cfg.CollectWindowTitle, cfg.SyncIntervalSeconds, cfg.HeartbeatIntervalSeconds)
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
	return policy
}
