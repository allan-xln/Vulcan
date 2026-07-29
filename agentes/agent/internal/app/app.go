package app

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"runtime"
	"sync"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/collectors"
	"github.com/lanfuture/vulcan/agentes/agent/internal/config"
	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	"github.com/lanfuture/vulcan/agentes/agent/internal/identity"
	vlogging "github.com/lanfuture/vulcan/agentes/agent/internal/logging"
	"github.com/lanfuture/vulcan/agentes/agent/internal/policy"
	"github.com/lanfuture/vulcan/agentes/agent/internal/queue"
	"github.com/lanfuture/vulcan/agentes/agent/internal/transport"
)

var ErrRestartRequested = errors.New("agent restart requested by approved command")

type Runtime struct {
	paths   config.Paths
	version string
	cfg     config.Config
	client  *transport.Client
	queue   *queue.Queue
	policy  *policy.Store
	current policy.Effective
	logger  *slog.Logger
	closer  interface{ Close() error }

	collectorList []contracts.Collector
	nextRun       map[string]time.Time
	moduleStatus  map[string]string
	lastError     string
	mu            sync.RWMutex
}

func New(paths config.Paths, version string) (*Runtime, error) {
	cfg, err := config.Load(paths)
	if err != nil {
		return nil, fmt.Errorf("load enrollment config: %w", err)
	}
	material, err := identity.LoadOrCreate(paths.DataDir)
	if err != nil {
		return nil, fmt.Errorf("load agent identity: %w", err)
	}
	policyStore, err := policy.NewStore(
		paths.DataDir,
		cfg.PolicySigningPublicKey,
		cfg.TenantID,
		cfg.AgentID,
		cfg.Profile,
	)
	if err != nil {
		return nil, err
	}
	effective, err := policyStore.Load()
	if err != nil {
		return nil, fmt.Errorf("load signed policy: %w", err)
	}
	eventQueue, err := queue.Open(paths.DataDir, queueLimits(effective.Document))
	if err != nil {
		return nil, fmt.Errorf("open encrypted offline queue: %w", err)
	}
	transportOptions := []transport.Option{}
	if cfg.AllowInsecurePrivateNetwork {
		transportOptions = append(transportOptions, transport.WithInsecurePrivateNetwork())
	}
	client, err := transport.New(cfg.ServerURL, cfg.AgentID, material.PrivateKey, version, transportOptions...)
	if err != nil {
		eventQueue.Close()
		return nil, err
	}
	logger, closer, err := vlogging.New(paths.LogDir, slog.LevelInfo)
	if err != nil {
		eventQueue.Close()
		return nil, err
	}
	agentRuntime := &Runtime{
		paths:        paths,
		version:      version,
		cfg:          cfg,
		client:       client,
		queue:        eventQueue,
		policy:       policyStore,
		current:      effective,
		logger:       logger,
		closer:       closer,
		nextRun:      make(map[string]time.Time),
		moduleStatus: make(map[string]string),
	}
	agentRuntime.collectorList = []contracts.Collector{
		collectors.NewSystemHealth(cfg.Profile),
		collectors.NewInventory(cfg.Profile),
		collectors.NewNetwork(cfg.Profile),
		collectors.NewActivity(cfg.Profile),
		collectors.NewServerChecks(cfg.Profile),
		collectors.NewDiscovery(cfg.Profile),
	}
	agentRuntime.configureCollectors()
	return agentRuntime, nil
}

func (agent *Runtime) Close() {
	_ = agent.queue.Close()
	_ = agent.closer.Close()
}

func (agent *Runtime) Run(ctx context.Context) error {
	defer agent.Close()
	agent.logger.Info("agent startup",
		"profile", agent.cfg.Profile,
		"version", agent.version,
		"agentId", agent.cfg.AgentID,
	)
	defer agent.logger.Info("agent shutdown")

	scheduler := time.NewTicker(time.Second)
	defer scheduler.Stop()
	heartbeat := time.NewTicker(time.Minute)
	defer heartbeat.Stop()
	syncTicker := time.NewTicker(policy.Interval(agent.current.Document, "sync", 30*time.Second))
	defer syncTicker.Stop()

	if err := agent.collectDue(ctx, true); err != nil {
		agent.setError(err)
	}
	if err := agent.sendHeartbeat(ctx); err != nil {
		agent.setError(err)
	}
	if err := agent.flush(ctx); err != nil {
		agent.setError(err)
	}

	for {
		select {
		case <-ctx.Done():
			shutdownContext, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			_ = agent.flush(shutdownContext)
			cancel()
			return nil
		case <-scheduler.C:
			if err := agent.collectDue(ctx, false); err != nil {
				agent.setError(err)
			}
		case <-heartbeat.C:
			if err := agent.sendHeartbeat(ctx); err != nil {
				agent.setError(err)
			}
		case <-syncTicker.C:
			if err := agent.flush(ctx); err != nil {
				agent.setError(err)
			}
		}
	}
}

func (agent *Runtime) configureCollectors() {
	now := time.Now()
	for _, collector := range agent.collectorList {
		name := collector.Name()
		if !policy.ModuleEnabled(agent.current.Document, name) {
			agent.moduleStatus[name] = "disabled_by_policy"
			continue
		}
		if !collector.Supported(context.Background()) {
			agent.moduleStatus[name] = "unsupported"
			continue
		}
		if err := collector.Configure(policy.Module(agent.current.Document, name)); err != nil {
			agent.moduleStatus[name] = "invalid_policy"
			agent.logger.Error("collector policy rejected", "collector", name, "error", err)
			continue
		}
		agent.moduleStatus[name] = "enabled"
		agent.nextRun[name] = now
	}
}

func (agent *Runtime) collectDue(ctx context.Context, initial bool) error {
	now := time.Now()
	var firstError error
	for _, collector := range agent.collectorList {
		name := collector.Name()
		if agent.moduleStatus[name] != "enabled" || now.Before(agent.nextRun[name]) {
			continue
		}
		events, err := collector.Collect(ctx)
		if err != nil {
			agent.moduleStatus[name] = "degraded"
			agent.logger.Warn("collector failed", "collector", name, "error", err)
			if firstError == nil {
				firstError = fmt.Errorf("%s collector: %w", name, err)
			}
		} else {
			agent.moduleStatus[name] = "enabled"
			for _, event := range events {
				if err := agent.queue.Enqueue(ctx, event, priorityFor(event)); err != nil && firstError == nil {
					firstError = err
				}
			}
		}
		agent.nextRun[name] = now.Add(agent.collectorInterval(name, initial))
	}
	return firstError
}

func (agent *Runtime) collectorInterval(name string, initial bool) time.Duration {
	switch name {
	case "inventory":
		if initial {
			return policy.Interval(agent.current.Document, name, 6*time.Hour)
		}
		return policy.Interval(agent.current.Document, name, 6*time.Hour)
	case "activity":
		return policy.Interval(agent.current.Document, name, 5*time.Second)
	case "serverChecks", "discovery":
		return policy.Interval(agent.current.Document, name, 5*time.Minute)
	default:
		return policy.Interval(agent.current.Document, name, time.Minute)
	}
}

func (agent *Runtime) flush(ctx context.Context) error {
	items, err := agent.queue.Peek(ctx, batchSize(agent.current.Document))
	if err != nil {
		return err
	}
	if len(items) == 0 {
		return nil
	}
	events := make([]contracts.Event, 0, len(items))
	ids := make([]string, 0, len(items))
	for _, item := range items {
		events = append(events, item.Event)
		ids = append(ids, item.ID)
	}
	response, err := agent.client.Events(ctx, contracts.EventsRequest{
		BatchID: randomUUID(),
		Events:  events,
	})
	if err != nil {
		_ = agent.queue.Fail(ctx, ids)
		agent.logger.Warn("event batch upload failed", "events", len(events), "error", err)
		return err
	}
	acknowledged := make(map[string]struct{}, len(response.AcknowledgedEventIDs))
	for _, id := range response.AcknowledgedEventIDs {
		acknowledged[id] = struct{}{}
	}
	ackIDs := make([]string, 0, len(ids))
	for _, id := range ids {
		if _, ok := acknowledged[id]; ok {
			ackIDs = append(ackIDs, id)
		}
	}
	if err := agent.queue.Ack(ctx, ackIDs); err != nil {
		return err
	}
	agent.logger.Info("event batch acknowledged",
		"received", response.Received,
		"stored", response.Stored,
		"duplicates", response.Duplicates,
	)
	return nil
}

func (agent *Runtime) sendHeartbeat(ctx context.Context) error {
	stats, err := agent.queue.Stats(ctx)
	if err != nil {
		return err
	}
	var memory runtime.MemStats
	runtime.ReadMemStats(&memory)
	agent.mu.RLock()
	lastError := agent.lastError
	agent.mu.RUnlock()
	response, err := agent.client.Heartbeat(ctx, contracts.HeartbeatRequest{
		Status:         "online",
		AgentVersion:   agent.version,
		QueueDepth:     stats.Depth,
		PolicyRevision: agent.current.Revision,
		PolicyStatus:   agent.cfg.PolicyStatus,
		LocalIP:        localIP(),
		LastError:      lastError,
		Modules:        cloneStatus(agent.moduleStatus),
		Performance: map[string]float64{
			"goHeapBytes": float64(memory.HeapAlloc),
			"goroutines":  float64(runtime.NumGoroutine()),
		},
	})
	if err != nil {
		return err
	}
	if response.Policy != nil && response.Policy.Revision != agent.current.Revision {
		effective, applyErr := agent.policy.Apply(*response.Policy)
		if applyErr != nil {
			agent.cfg.PolicyStatus = "rejected"
			_ = config.Save(agent.paths, agent.cfg)
			agent.logger.Error("signed policy rejected", "error", applyErr)
			return applyErr
		}
		agent.current = effective
		agent.cfg.PolicyRevision = effective.Revision
		agent.cfg.PolicyStatus = "applied"
		if err := config.Save(agent.paths, agent.cfg); err != nil {
			return err
		}
		agent.configureCollectors()
		agent.logger.Info("signed policy applied", "revision", effective.Revision)
	}
	for _, command := range response.Commands {
		if err := agent.handleCommand(ctx, command); err != nil {
			_ = agent.client.CommandResult(ctx, command.CommandID, "failed", err.Error())
			if errors.Is(err, ErrRestartRequested) {
				return err
			}
			continue
		}
		_ = agent.client.CommandResult(ctx, command.CommandID, "succeeded", "Comando seguro concluído.")
	}
	agent.mu.Lock()
	agent.lastError = ""
	agent.mu.Unlock()
	return nil
}

func (agent *Runtime) handleCommand(ctx context.Context, command contracts.Command) error {
	switch command.CommandType {
	case "refresh_policy":
		envelope, err := agent.client.Policy(ctx)
		if err != nil {
			return err
		}
		effective, err := agent.policy.Apply(envelope)
		if err != nil {
			return err
		}
		agent.current = effective
		agent.configureCollectors()
		return nil
	case "request_inventory":
		agent.nextRun["inventory"] = time.Now()
		return agent.collectDue(ctx, false)
	case "request_diagnostics":
		stats, err := agent.queue.Stats(ctx)
		if err != nil {
			return err
		}
		event := collectorsDiagnostic(agent, stats)
		return agent.queue.Enqueue(ctx, event, queue.PriorityAudit)
	case "restart_agent":
		return ErrRestartRequested
	default:
		return fmt.Errorf("command type %s is unsupported by this build", command.CommandType)
	}
}

func (agent *Runtime) setError(err error) {
	agent.mu.Lock()
	agent.lastError = err.Error()
	agent.mu.Unlock()
}

func priorityFor(event contracts.Event) int {
	switch event.Severity {
	case "critical", "error":
		return queue.PriorityCritical
	}
	switch event.Category {
	case "audit":
		return queue.PriorityAudit
	case "session":
		return queue.PrioritySession
	case "health", "service", "discovery":
		return queue.PriorityHealth
	case "workforce":
		return queue.PriorityProductivity
	default:
		return queue.PriorityMetrics
	}
}

func queueLimits(document map[string]any) queue.Limits {
	settings, _ := document["queue"].(map[string]any)
	return queue.Limits{
		MaxEvents: int(number(settings["maxEvents"], 10000)),
		MaxBytes:  number(settings["maxBytes"], 100*1024*1024),
		Retention: time.Duration(number(settings["retentionHours"], 168)) * time.Hour,
	}
}

func batchSize(document map[string]any) int {
	settings, _ := document["queue"].(map[string]any)
	value := int(number(settings["batchSize"], 100))
	if value < 1 {
		return 1
	}
	if value > 500 {
		return 500
	}
	return value
}

func number(value any, fallback int64) int64 {
	switch typed := value.(type) {
	case float64:
		return int64(typed)
	case int64:
		return typed
	case int:
		return int64(typed)
	default:
		return fallback
	}
}

func cloneStatus(values map[string]string) map[string]string {
	cloned := make(map[string]string, len(values))
	for key, value := range values {
		cloned[key] = value
	}
	return cloned
}

func localIP() string {
	connection, err := net.DialTimeout("udp", "1.1.1.1:53", time.Second)
	if err != nil {
		return ""
	}
	defer connection.Close()
	address, _ := connection.LocalAddr().(*net.UDPAddr)
	if address == nil {
		return ""
	}
	return address.IP.String()
}

func randomUUID() string {
	data := make([]byte, 16)
	if _, err := rand.Read(data); err != nil {
		return fmt.Sprintf("%d-0000-4000-8000-000000000000", time.Now().Unix())
	}
	data[6] = (data[6] & 0x0f) | 0x40
	data[8] = (data[8] & 0x3f) | 0x80
	encoded := hex.EncodeToString(data)
	return fmt.Sprintf("%s-%s-%s-%s-%s", encoded[:8], encoded[8:12], encoded[12:16], encoded[16:20], encoded[20:])
}

func collectorsDiagnostic(agent *Runtime, stats queue.Stats) contracts.Event {
	return contracts.Event{
		EventID:               randomUUID(),
		SchemaVersion:         contracts.EventSchemaVersion,
		EventType:             "agent.diagnostics.snapshot",
		Category:              "audit",
		Severity:              "info",
		OccurredAt:            time.Now().UTC(),
		Context:               map[string]any{"modules": cloneStatus(agent.moduleStatus)},
		Metrics:               map[string]any{"queueDepth": stats.Depth, "queueBytes": stats.EncryptedBytes},
		Message:               "O agente gerou um diagnóstico seguro solicitado pelo administrador.",
		Fingerprint:           randomUUID(),
		PrivacyClassification: "operational",
		RetentionPolicy:       "standard",
	}
}
