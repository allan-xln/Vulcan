package collectors

import (
	"context"
	"fmt"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	gnet "github.com/shirou/gopsutil/v4/net"
)

type Network struct {
	profile contracts.Profile
	policy  map[string]any
}

func NewNetwork(profile contracts.Profile) *Network {
	return &Network{profile: profile}
}

func (collector *Network) Name() string { return "network" }
func (collector *Network) Profiles() []contracts.Profile {
	return []contracts.Profile{
		contracts.ProfileWorkstation,
		contracts.ProfileServer,
		contracts.ProfileCollector,
	}
}
func (collector *Network) Supported(context.Context) bool {
	return profileSupported(collector.profile, collector.Profiles())
}
func (collector *Network) Configure(policy map[string]any) error {
	collector.policy = policy
	return nil
}
func (collector *Network) Health(context.Context) contracts.Health {
	return contracts.Health{Status: "ok"}
}

func (collector *Network) Collect(ctx context.Context) ([]contracts.Event, error) {
	interfaces, err := gnet.InterfacesWithContext(ctx)
	if err != nil {
		return nil, fmt.Errorf("collect network interfaces: %w", err)
	}
	counters, err := gnet.IOCountersWithContext(ctx, true)
	if err != nil {
		return nil, fmt.Errorf("collect network counters: %w", err)
	}
	counterByName := make(map[string]gnet.IOCountersStat, len(counters))
	for _, counter := range counters {
		counterByName[counter.Name] = counter
	}
	items := make([]map[string]any, 0, len(interfaces))
	for _, networkInterface := range interfaces {
		addresses := make([]string, 0, len(networkInterface.Addrs))
		for _, address := range networkInterface.Addrs {
			addresses = append(addresses, address.Addr)
		}
		counter := counterByName[networkInterface.Name]
		items = append(items, map[string]any{
			"name":          networkInterface.Name,
			"mac":           networkInterface.HardwareAddr,
			"addresses":     addresses,
			"flags":         networkInterface.Flags,
			"bytesSent":     counter.BytesSent,
			"bytesReceived": counter.BytesRecv,
			"errorsIn":      counter.Errin,
			"errorsOut":     counter.Errout,
			"dropsIn":       counter.Dropin,
			"dropsOut":      counter.Dropout,
		})
	}
	return []contracts.Event{
		newEvent(
			"network.interfaces.sample",
			"network",
			"info",
			"As interfaces de rede do equipamento foram verificadas.",
			map[string]any{"interfaces": items},
			nil,
		),
	}, nil
}
