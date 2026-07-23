//go:build windows

package config

func isPrivilegedInstall() bool {
	return true
}
