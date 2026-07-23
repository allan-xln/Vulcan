//go:build !windows

package config

import "os"

func isPrivilegedInstall() bool {
	return os.Geteuid() == 0
}
