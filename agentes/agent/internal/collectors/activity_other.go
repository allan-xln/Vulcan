//go:build !linux && !windows

package collectors

import (
	"context"
	"errors"
	"time"
)

func platformActivitySupported(context.Context) bool {
	return false
}

func platformActivity(context.Context) (activeWindow, time.Duration, error) {
	return activeWindow{}, 0, errors.New("activity collection is unsupported on this operating system")
}
