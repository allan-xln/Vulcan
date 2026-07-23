//go:build windows

package identity

import (
	"errors"
	"strings"

	"golang.org/x/sys/windows/registry"
)

func platformDeviceID() (string, error) {
	key, err := registry.OpenKey(
		registry.LOCAL_MACHINE,
		`SOFTWARE\Microsoft\Cryptography`,
		registry.QUERY_VALUE|registry.WOW64_64KEY,
	)
	if err != nil {
		return "", err
	}
	defer key.Close()
	value, _, err := key.GetStringValue("MachineGuid")
	if err != nil {
		return "", err
	}
	if strings.TrimSpace(value) == "" {
		return "", errors.New("Windows MachineGuid is empty")
	}
	return strings.TrimSpace(value), nil
}
