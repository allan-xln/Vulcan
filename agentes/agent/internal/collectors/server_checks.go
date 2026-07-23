package collectors

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

type ServerChecks struct {
	profile contracts.Profile
	module  map[string]any
}

func NewServerChecks(profile contracts.Profile) *ServerChecks {
	return &ServerChecks{profile: profile}
}

func (collector *ServerChecks) Name() string { return "serverChecks" }
func (collector *ServerChecks) Profiles() []contracts.Profile {
	return []contracts.Profile{contracts.ProfileServer, contracts.ProfileCollector}
}
func (collector *ServerChecks) Supported(context.Context) bool {
	return profileSupported(collector.profile, collector.Profiles())
}
func (collector *ServerChecks) Configure(module map[string]any) error {
	collector.module = module
	return nil
}
func (collector *ServerChecks) Health(context.Context) contracts.Health {
	return contracts.Health{Status: "ok"}
}

func (collector *ServerChecks) Collect(ctx context.Context) ([]contracts.Event, error) {
	rawChecks, _ := collector.module["checks"].([]any)
	events := make([]contracts.Event, 0, len(rawChecks))
	for _, raw := range rawChecks {
		check, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		checkType, _ := check["type"].(string)
		name, _ := check["name"].(string)
		if name == "" {
			name = "Serviço configurado"
		}
		started := time.Now()
		var err error
		switch checkType {
		case "http":
			err = runHTTPCheck(ctx, check)
		case "tcp":
			err = runTCPCheck(ctx, check)
		default:
			continue
		}
		duration := time.Since(started)
		severity := "info"
		message := fmt.Sprintf("%s está disponível.", name)
		contextData := map[string]any{"name": name, "type": checkType}
		if err != nil {
			severity = "warning"
			message = fmt.Sprintf("%s não respondeu como esperado e pode afetar usuários ou dependências.", name)
			contextData["error"] = err.Error()
		}
		events = append(events, newEvent(
			"service.health.check",
			"service",
			severity,
			message,
			contextData,
			map[string]any{"durationMilliseconds": duration.Milliseconds(), "available": err == nil},
		))
	}
	return events, nil
}

func runHTTPCheck(ctx context.Context, check map[string]any) error {
	target, _ := check["url"].(string)
	parsed, err := url.Parse(target)
	if err != nil || parsed.Hostname() == "" {
		return errors.New("invalid HTTP health URL")
	}
	if parsed.Scheme != "https" && !(parsed.Scheme == "http" && isLoopbackHost(parsed.Hostname())) {
		return errors.New("HTTP health checks require HTTPS outside loopback")
	}
	timeout := checkTimeout(check)
	requestContext, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	request, err := http.NewRequestWithContext(requestContext, http.MethodGet, parsed.String(), nil)
	if err != nil {
		return err
	}
	response, err := (&http.Client{Timeout: timeout}).Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	minimumStatus := 200
	maximumStatus := 399
	if expected, ok := check["expectedStatus"].(float64); ok {
		minimumStatus, maximumStatus = int(expected), int(expected)
	}
	if response.StatusCode < minimumStatus || response.StatusCode > maximumStatus {
		return fmt.Errorf("unexpected HTTP status %d", response.StatusCode)
	}
	return nil
}

func runTCPCheck(ctx context.Context, check map[string]any) error {
	host, _ := check["host"].(string)
	portValue, ok := check["port"].(float64)
	if host == "" || !ok || portValue < 1 || portValue > 65535 {
		return errors.New("invalid TCP health target")
	}
	timeout := checkTimeout(check)
	dialer := net.Dialer{Timeout: timeout}
	connection, err := dialer.DialContext(ctx, "tcp", net.JoinHostPort(host, strconv.Itoa(int(portValue))))
	if err != nil {
		return err
	}
	return connection.Close()
}

func checkTimeout(check map[string]any) time.Duration {
	if seconds, ok := check["timeoutSeconds"].(float64); ok && seconds >= 1 && seconds <= 30 {
		return time.Duration(seconds) * time.Second
	}
	return 5 * time.Second
}

func isLoopbackHost(host string) bool {
	return host == "localhost" || host == "127.0.0.1" || host == "::1" ||
		strings.HasPrefix(host, "127.")
}
