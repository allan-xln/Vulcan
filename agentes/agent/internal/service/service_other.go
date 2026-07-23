//go:build !windows

package service

import (
	"context"
	"errors"
)

const Name = "vulcan-agent"

func RunIfService(func(context.Context) error) (bool, error) {
	return false, nil
}

func Install() error {
	return errors.New("Linux service installation is provided by the .deb package and systemd unit")
}

func Uninstall() error {
	return errors.New("Linux service removal is provided by the package manager")
}

func ProtectData(string) error {
	return errors.New("data ACL preparation is implemented only on Windows")
}

func ConfigureRecovery() error {
	return errors.New("service recovery configuration is implemented only on Windows")
}
