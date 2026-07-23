//go:build !windows

package identity

import (
	"errors"
	"os"
	"strings"
)

func platformDeviceID() (string, error) {
	for _, path := range []string{"/etc/machine-id", "/var/lib/dbus/machine-id"} {
		data, err := os.ReadFile(path)
		if err == nil && strings.TrimSpace(string(data)) != "" {
			return strings.TrimSpace(string(data)), nil
		}
	}
	return "", errors.New("stable machine ID is unavailable")
}
