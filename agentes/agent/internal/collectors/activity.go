package collectors

import (
	"context"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

type activeWindow struct {
	Process string
	Title   string
}

type Activity struct {
	profile       contracts.Profile
	module        map[string]any
	last          activeWindow
	lastChangedAt time.Time
	idle          bool
	idleThreshold time.Duration
}

func NewActivity(profile contracts.Profile) *Activity {
	return &Activity{profile: profile, idleThreshold: 5 * time.Minute}
}

func (collector *Activity) Name() string { return "activity" }
func (collector *Activity) Profiles() []contracts.Profile {
	return []contracts.Profile{contracts.ProfileWorkstation}
}
func (collector *Activity) Supported(ctx context.Context) bool {
	return collector.profile == contracts.ProfileWorkstation && platformActivitySupported(ctx)
}
func (collector *Activity) Configure(module map[string]any) error {
	collector.module = module
	if seconds, ok := module["idleThresholdSeconds"].(float64); ok && seconds >= 60 && seconds <= 7200 {
		collector.idleThreshold = time.Duration(seconds) * time.Second
	}
	return nil
}
func (collector *Activity) Health(ctx context.Context) contracts.Health {
	if !collector.Supported(ctx) {
		return contracts.Health{
			Status:  "unsupported",
			Message: "foreground activity requires an accessible interactive desktop session",
		}
	}
	return contracts.Health{Status: "ok"}
}

func (collector *Activity) Collect(ctx context.Context) ([]contracts.Event, error) {
	window, idleDuration, err := platformActivity(ctx)
	if err != nil {
		return nil, err
	}
	now := time.Now()
	events := make([]contracts.Event, 0, 2)
	isIdle := idleDuration >= collector.idleThreshold
	if isIdle != collector.idle {
		eventType := "workstation.idle.ended"
		message := "O usuário retomou a sessão de trabalho."
		if isIdle {
			eventType = "workstation.idle.started"
			message = "A sessão entrou em período ocioso."
		}
		events = append(events, newEvent(
			eventType,
			"workforce",
			"info",
			message,
			nil,
			map[string]any{"idleSeconds": int64(idleDuration.Seconds())},
		))
		collector.idle = isIdle
	}
	if window.Process != "" && window != collector.last {
		contextData := map[string]any{
			"processName": window.Process,
		}
		if titles, _ := collector.module["windowTitles"].(bool); titles && !sensitiveTitle(window.Title) {
			contextData["windowTitle"] = window.Title
		}
		metrics := map[string]any{}
		if !collector.lastChangedAt.IsZero() {
			metrics["durationSeconds"] = int64(now.Sub(collector.lastChangedAt).Seconds())
			contextData["previousProcessName"] = collector.last.Process
		}
		events = append(events, newEvent(
			"workstation.activity.changed",
			"workforce",
			"info",
			"O contexto de trabalho mudou para outro aplicativo.",
			contextData,
			metrics,
		))
		collector.last = window
		collector.lastChangedAt = now
	}
	return events, nil
}

func sensitiveTitle(title string) bool {
	lower := []rune(title)
	for index, value := range lower {
		if value >= 'A' && value <= 'Z' {
			lower[index] = value + ('a' - 'A')
		}
	}
	text := string(lower)
	for _, word := range []string{"password", "senha", "auth", "login", "bank", "banco", "1password", "bitwarden", "keepass"} {
		if containsText(text, word) {
			return true
		}
	}
	return false
}

func containsText(text, fragment string) bool {
	if len(fragment) == 0 || len(text) < len(fragment) {
		return false
	}
	for index := 0; index <= len(text)-len(fragment); index++ {
		if text[index:index+len(fragment)] == fragment {
			return true
		}
	}
	return false
}
