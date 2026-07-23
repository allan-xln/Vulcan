package collectors

import (
	"context"
	"fmt"
	"runtime"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	"github.com/shirou/gopsutil/v4/cpu"
	"github.com/shirou/gopsutil/v4/disk"
	"github.com/shirou/gopsutil/v4/host"
	"github.com/shirou/gopsutil/v4/mem"
	gnet "github.com/shirou/gopsutil/v4/net"
)

type Inventory struct {
	profile contracts.Profile
	policy  map[string]any
}

func NewInventory(profile contracts.Profile) *Inventory {
	return &Inventory{profile: profile}
}

func (collector *Inventory) Name() string { return "inventory" }
func (collector *Inventory) Profiles() []contracts.Profile {
	return []contracts.Profile{
		contracts.ProfileWorkstation,
		contracts.ProfileServer,
		contracts.ProfileCollector,
	}
}
func (collector *Inventory) Supported(context.Context) bool {
	return profileSupported(collector.profile, collector.Profiles())
}
func (collector *Inventory) Configure(policy map[string]any) error {
	collector.policy = policy
	return nil
}
func (collector *Inventory) Health(context.Context) contracts.Health {
	return contracts.Health{Status: "ok"}
}

func (collector *Inventory) Collect(ctx context.Context) ([]contracts.Event, error) {
	hostInfo, err := host.InfoWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect host inventory: %w", err)
	}
	processors, err := cpu.InfoWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect CPU inventory: %w", err)
	}
	memory, err := mem.VirtualMemoryWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect memory inventory: %w", err)
	}
	partitions, err := disk.PartitionsWithContext(ctx, false)
	if err != nil {
		return nil, fmt.Errorf("collect disk inventory: %w", err)
	}
	interfaces, err := gnet.InterfacesWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect network inventory: %w", err)
	}
	cpuModels := make([]string, 0, len(processors))
	for _, processor := range processors {
		if processor.ModelName != "" && !contains(cpuModels, processor.ModelName) {
			cpuModels = append(cpuModels, processor.ModelName)
		}
	}
	disks := make([]map[string]any, 0, len(partitions))
	for _, partition := range partitions {
		disks = append(disks, map[string]any{
			"device": partition.Device,
			"mount":  partition.Mountpoint,
			"fstype": partition.Fstype,
		})
	}
	network := make([]map[string]any, 0, len(interfaces))
	for _, networkInterface := range interfaces {
		addresses := make([]string, 0, len(networkInterface.Addrs))
		for _, address := range networkInterface.Addrs {
			addresses = append(addresses, address.Addr)
		}
		network = append(network, map[string]any{
			"name":      networkInterface.Name,
			"mac":       networkInterface.HardwareAddr,
			"addresses": addresses,
			"mtu":       networkInterface.MTU,
		})
	}
	contextData := map[string]any{
		"hostname":           hostInfo.Hostname,
		"operatingSystem":    hostInfo.OS,
		"platform":           hostInfo.Platform,
		"platformFamily":     hostInfo.PlatformFamily,
		"platformVersion":    hostInfo.PlatformVersion,
		"kernelVersion":      hostInfo.KernelVersion,
		"kernelArchitecture": hostInfo.KernelArch,
		"architecture":       runtime.GOARCH,
		"virtualization":     hostInfo.VirtualizationSystem,
		"virtualizationRole": hostInfo.VirtualizationRole,
		"cpuModels":          cpuModels,
		"logicalCores":       runtime.NumCPU(),
		"memoryTotalBytes":   memory.Total,
		"disks":              disks,
		"interfaces":         network,
	}
	return []contracts.Event{
		newEvent(
			"endpoint.inventory.snapshot",
			"inventory",
			"info",
			"O inventário do equipamento foi atualizado.",
			contextData,
			nil,
		),
	}, nil
}

func contains(values []string, candidate string) bool {
	for _, value := range values {
		if value == candidate {
			return true
		}
	}
	return false
}
