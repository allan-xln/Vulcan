//go:build windows

package collectors

import (
	"context"
	"errors"
	"path/filepath"
	"syscall"
	"time"
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	user32                       = windows.NewLazySystemDLL("user32.dll")
	kernel32                     = windows.NewLazySystemDLL("kernel32.dll")
	procGetForegroundWindow      = user32.NewProc("GetForegroundWindow")
	procGetWindowTextLengthW     = user32.NewProc("GetWindowTextLengthW")
	procGetWindowTextW           = user32.NewProc("GetWindowTextW")
	procGetWindowThreadProcessID = user32.NewProc("GetWindowThreadProcessId")
	procGetLastInputInfo         = user32.NewProc("GetLastInputInfo")
	procGetTickCount64           = kernel32.NewProc("GetTickCount64")
)

type lastInputInfo struct {
	Size uint32
	Time uint32
}

func platformActivitySupported(context.Context) bool {
	window, _, _ := procGetForegroundWindow.Call()
	return window != 0
}

func platformActivity(context.Context) (activeWindow, time.Duration, error) {
	window, _, _ := procGetForegroundWindow.Call()
	if window == 0 {
		return activeWindow{}, 0, errors.New("interactive session has no active window")
	}
	length, _, _ := procGetWindowTextLengthW.Call(window)
	titleBuffer := make([]uint16, length+1)
	if length > 0 {
		_, _, _ = procGetWindowTextW.Call(
			window,
			uintptr(unsafe.Pointer(&titleBuffer[0])),
			uintptr(len(titleBuffer)),
		)
	}
	var processID uint32
	_, _, _ = procGetWindowThreadProcessID.Call(window, uintptr(unsafe.Pointer(&processID)))
	processName := ""
	if processID != 0 {
		process, err := windows.OpenProcess(windows.PROCESS_QUERY_LIMITED_INFORMATION, false, processID)
		if err == nil {
			defer windows.CloseHandle(process)
			buffer := make([]uint16, windows.MAX_PATH)
			size := uint32(len(buffer))
			if windows.QueryFullProcessImageName(process, 0, &buffer[0], &size) == nil {
				processName = filepath.Base(syscall.UTF16ToString(buffer[:size]))
			}
		}
	}
	info := lastInputInfo{Size: uint32(unsafe.Sizeof(lastInputInfo{}))}
	idle := time.Duration(0)
	success, _, _ := procGetLastInputInfo.Call(uintptr(unsafe.Pointer(&info)))
	if success != 0 {
		ticks, _, _ := procGetTickCount64.Call()
		idle = time.Duration(uint64(ticks)-uint64(info.Time)) * time.Millisecond
	}
	return activeWindow{
		Process: processName,
		Title:   syscall.UTF16ToString(titleBuffer),
	}, idle, nil
}
