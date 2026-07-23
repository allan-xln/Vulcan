package collectors

import (
	"context"
	"fmt"
	"os"
	"runtime"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/host"
	"github.com/shirou/gopsutil/v4/mem"
)

type SystemHealth struct {
	profile contracts.Profile
	policy  map[string]any
}

func NewSystemHealth(profile contracts.Profile) *SystemHealth {
	return &SystemHealth{profile: profile}
}

func (collector *SystemHealth) Name() string { return "systemMetrics" }
func (collector *SystemHealth) Profiles() []contracts.Profile {
	return []contracts.Profile{
		contracts.ProfileWorkstation,
		contracts.ProfileServer,
		contracts.ProfileCollector,
	}
}
func (collector *SystemHealth) Supported(context.Context) bool {
	return profileSupported(collector.profile, collector.Profiles())
}
func (collector *SystemHealth) Configure(policy map[string]any) error {
	collector.policy = policy
	return nil
}
func (collector *SystemHealth) Health(context.Context) contracts.Health {
	return contracts.Health{Status: "ok"}
}

func (collector *SystemHealth) Collect(ctx context.Context) ([]contracts.Event, error) {
	cpuPercent, err := cpu.PercentWithContext(ctx, 200*time.Millisecond, false)
	if err != nil {
		return nil, fmt.Errorf("collect CPU: %w", err)
	}
	memory, err := mem.VirtualMemoryWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect memory: %w", err)
	}
	path := "/"
	if runtime.GOOS == "windows" {
		path = os.Getenv("SystemDrive") + `\`
		if path == `\` {
			path = `C:\`
		}
	}
	storage, err := disk.UsageWithContext(ctx, path)
	if err != nil {
		return nil, fmt.Errorf("collect disk: %w", err)
	}
	uptime, err := host.UptimeWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect uptime: %w", err)
	}
	metrics := map[string]any{
		"cpuPercent":       first(cpuPercent),
		"memoryPercent":    memory.UsedPercent,
		"memoryUsedBytes":  memory.Used,
		"memoryTotalBytes": memory.Total,
		"diskPercent":      storage.UsedPercent,
		"diskUsedBytes":    storage.Used,
		"diskTotalBytes":   storage.Total,
		"uptimeSeconds":    uptime,
	}
	severity := "info"
	message := "A saúde do equipamento está dentro dos limites operacionais."
	if first(cpuPercent) >= 95 || memory.UsedPercent >= 95 || storage.UsedPercent >= 95 {
		severity = "warning"
		message = "O equipamento está próximo do limite de recursos e pode afetar o trabalho ou os serviços."
	}
	return []contracts.Event{
		newEvent("endpoint.health.sample", "health", severity, message, nil, metrics),
	}, nil
}

func first(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	return values[0]
}
