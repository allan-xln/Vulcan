//go:build linux

package collectors

import (
	"context"
	"errors"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"
)

var windowIDPattern = regexp.MustCompile(`0x[0-9a-fA-F]+`)

func platformActivitySupported(context.Context) bool {
	if os.Getenv("DISPLAY") == "" {
		return false
	}
	_, err := exec.LookPath("xprop")
	return err == nil
}

func platformActivity(ctx context.Context) (activeWindow, time.Duration, error) {
	commandContext, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	rootOutput, err := exec.CommandContext(commandContext, "xprop", "-root", "_NET_ACTIVE_WINDOW").Output()
	if err != nil {
		return activeWindow{}, 0, err
	}
	windowID := windowIDPattern.FindString(string(rootOutput))
	if windowID == "" || windowID == "0x0" {
		return activeWindow{}, 0, errors.New("interactive session has no active window")
	}
	windowOutput, err := exec.CommandContext(
		commandContext,
		"xprop",
		"-id",
		windowID,
		"WM_CLASS",
		"_NET_WM_NAME",
		"WM_NAME",
	).Output()
	if err != nil {
		return activeWindow{}, 0, err
	}
	process := propertyValue(string(windowOutput), "WM_CLASS")
	title := propertyValue(string(windowOutput), "_NET_WM_NAME")
	if title == "" {
		title = propertyValue(string(windowOutput), "WM_NAME")
	}
	idleDuration := time.Duration(0)
	if _, lookupErr := exec.LookPath("xprintidle"); lookupErr == nil {
		if output, commandErr := exec.CommandContext(commandContext, "xprintidle").Output(); commandErr == nil {
			milliseconds, parseErr := strconv.ParseInt(strings.TrimSpace(string(output)), 10, 64)
			if parseErr == nil {
				idleDuration = time.Duration(milliseconds) * time.Millisecond
			}
		}
	}
	return activeWindow{Process: process, Title: title}, idleDuration, nil
}

func propertyValue(output, property string) string {
	for _, line := range strings.Split(output, "\n") {
		if !strings.HasPrefix(line, property) {
			continue
		}
		separator := strings.Index(line, "=")
		if separator < 0 {
			return ""
		}
		value := strings.TrimSpace(line[separator+1:])
		parts := strings.Split(value, ",")
		value = strings.Trim(strings.TrimSpace(parts[len(parts)-1]), `"`)
		return value
	}
	return ""
}
