package collectors

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/netip"
	"strconv"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

type Discovery struct {
	profile contracts.Profile
	module  map[string]any
}

func NewDiscovery(profile contracts.Profile) *Discovery {
	return &Discovery{profile: profile}
}

func (collector *Discovery) Name() string { return "discovery" }
func (collector *Discovery) Profiles() []contracts.Profile {
	return []contracts.Profile{contracts.ProfileCollector}
}
func (collector *Discovery) Supported(context.Context) bool {
	return collector.profile == contracts.ProfileCollector
}
func (collector *Discovery) Configure(module map[string]any) error {
	if readOnly, ok := module["readOnly"].(bool); !ok || !readOnly {
		return errors.New("collector discovery requires readOnly=true")
	}
	if scan, _ := module["portScan"].(bool); scan {
		return errors.New("generic port scanning is not supported")
	}
	collector.module = module
	return nil
}
func (collector *Discovery) Health(context.Context) contracts.Health {
	if len(stringList(collector.module["allowedNetworks"])) == 0 {
		return contracts.Health{Status: "disabled", Message: "no allowed networks configured"}
	}
	return contracts.Health{Status: "ok"}
}

func (collector *Discovery) Collect(ctx context.Context) ([]contracts.Event, error) {
	allowed, err := parsePrefixes(stringList(collector.module["allowedNetworks"]))
	if err != nil {
		return nil, fmt.Errorf("parse allowed networks: %w", err)
	}
	if len(allowed) == 0 {
		return nil, nil
	}
	denied, err := parsePrefixes(stringList(collector.module["deniedNetworks"]))
	if err != nil {
		return nil, fmt.Errorf("parse denied networks: %w", err)
	}
	rawTargets, _ := collector.module["targets"].([]any)
	if len(rawTargets) > 256 {
		return nil, errors.New("safe discovery target limit is 256")
	}
	events := make([]contracts.Event, 0, len(rawTargets))
	for _, rawTarget := range rawTargets {
		target, ok := rawTarget.(map[string]any)
		if !ok {
			continue
		}
		host, _ := target["host"].(string)
		if host == "" {
			continue
		}
		lookupContext, cancel := context.WithTimeout(ctx, 3*time.Second)
		addresses, lookupErr := net.DefaultResolver.LookupNetIP(lookupContext, "ip", host)
		cancel()
		if lookupErr != nil {
			events = append(events, discoveryEvent(host, nil, false, lookupErr, nil))
			continue
		}
		approved := make([]netip.Addr, 0, len(addresses))
		for _, address := range addresses {
			address = address.Unmap()
			if containsAddress(allowed, address) && !containsAddress(denied, address) {
				approved = append(approved, address)
			}
		}
		if len(approved) == 0 {
			events = append(events, discoveryEvent(
				host,
				addresses,
				false,
				errors.New("resolved addresses are outside explicitly allowed networks"),
				nil,
			))
			continue
		}
		ports := numericList(target["ports"])
		if len(ports) > 8 {
			ports = ports[:8]
		}
		openPorts := make([]int, 0)
		for _, port := range ports {
			if port < 1 || port > 65535 {
				continue
			}
			dialer := net.Dialer{Timeout: 2 * time.Second}
			connection, dialErr := dialer.DialContext(
				ctx,
				"tcp",
				net.JoinHostPort(approved[0].String(), strconv.Itoa(port)),
			)
			if dialErr == nil {
				openPorts = append(openPorts, port)
				_ = connection.Close()
			}
		}
		events = append(events, discoveryEvent(host, approved, true, nil, openPorts))
	}
	return events, nil
}

func discoveryEvent(host string, addresses any, available bool, discoveryError error, ports []int) contracts.Event {
	contextData := map[string]any{
		"host":      host,
		"addresses": addresses,
		"openPorts": ports,
		"readOnly":  true,
	}
	severity := "info"
	message := fmt.Sprintf("%s foi identificado pela descoberta segura.", host)
	if discoveryError != nil {
		severity = "notice"
		message = fmt.Sprintf("%s não pôde ser validado pela descoberta segura.", host)
		contextData["error"] = discoveryError.Error()
	}
	return newEvent(
		"discovery.target.observed",
		"discovery",
		severity,
		message,
		contextData,
		map[string]any{"available": available},
	)
}

func parsePrefixes(values []string) ([]netip.Prefix, error) {
	prefixes := make([]netip.Prefix, 0, len(values))
	for _, value := range values {
		prefix, err := netip.ParsePrefix(value)
		if err != nil {
			return nil, err
		}
		prefixes = append(prefixes, prefix.Masked())
	}
	return prefixes, nil
}

func containsAddress(prefixes []netip.Prefix, address netip.Addr) bool {
	for _, prefix := range prefixes {
		if prefix.Contains(address) {
			return true
		}
	}
	return false
}

func stringList(value any) []string {
	raw, _ := value.([]any)
	values := make([]string, 0, len(raw))
	for _, item := range raw {
		if text, ok := item.(string); ok {
			values = append(values, text)
		}
	}
	if direct, ok := value.([]string); ok {
		return direct
	}
	return values
}

func numericList(value any) []int {
	raw, _ := value.([]any)
	values := make([]int, 0, len(raw))
	for _, item := range raw {
		if number, ok := item.(float64); ok {
			values = append(values, int(number))
		}
	}
	return values
}
