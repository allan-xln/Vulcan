//go:build windows

package service

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/mgr"
)

const Name = "VulcanAgent"

type handler struct {
	run func(context.Context) error
}

func (serviceHandler *handler) Execute(
	_ []string,
	requests <-chan svc.ChangeRequest,
	statuses chan<- svc.Status,
) (bool, uint32) {
	statuses <- svc.Status{State: svc.StartPending}
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	result := make(chan error, 1)
	go func() {
		result <- serviceHandler.run(ctx)
	}()
	statuses <- svc.Status{
		State:   svc.Running,
		Accepts: svc.AcceptStop | svc.AcceptShutdown,
	}
	for {
		select {
		case request := <-requests:
			switch request.Cmd {
			case svc.Interrogate:
				statuses <- request.CurrentStatus
			case svc.Stop, svc.Shutdown:
				statuses <- svc.Status{State: svc.StopPending}
				cancel()
			}
		case err := <-result:
			if err != nil {
				return false, 1
			}
			return false, 0
		}
	}
}

func RunIfService(run func(context.Context) error) (bool, error) {
	isService, err := svc.IsWindowsService()
	if err != nil || !isService {
		return isService, err
	}
	return true, svc.Run(Name, &handler{run: run})
}

func Install() error {
	executable, err := os.Executable()
	if err != nil {
		return err
	}
	executable, err = filepath.Abs(executable)
	if err != nil {
		return err
	}
	manager, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("connect Service Control Manager: %w", err)
	}
	defer manager.Disconnect()
	existing, err := manager.OpenService(Name)
	if err == nil {
		existing.Close()
		return errors.New("Vulcan Agent service is already installed")
	}
	programData := os.Getenv("ProgramData")
	if programData == "" {
		programData = `C:\ProgramData`
	}
	dataPath := filepath.Join(programData, "Vulcan", "Agent")
	if err := ProtectData(dataPath); err != nil {
		return err
	}
	created, err := manager.CreateService(
		Name,
		executable,
		mgr.Config{
			DisplayName:      "Vulcan Agent",
			Description:      "Vulcan operational intelligence, health and inventory agent.",
			StartType:        mgr.StartAutomatic,
			ServiceStartName: `NT AUTHORITY\LocalService`,
		},
		"run",
	)
	if err != nil {
		return fmt.Errorf("create Vulcan Agent service: %w", err)
	}
	defer created.Close()
	if err := setRecoveryActions(created); err != nil {
		_ = created.Delete()
		return err
	}
	if err := created.Start(); err != nil {
		_ = created.Delete()
		return fmt.Errorf("start Vulcan Agent service: %w", err)
	}
	return nil
}

func ConfigureRecovery() error {
	manager, err := mgr.Connect()
	if err != nil {
		return fmt.Errorf("connect Service Control Manager: %w", err)
	}
	defer manager.Disconnect()
	installed, err := manager.OpenService(Name)
	if err != nil {
		return errors.New("Vulcan Agent service is not installed")
	}
	defer installed.Close()
	return setRecoveryActions(installed)
}

func setRecoveryActions(installed *mgr.Service) error {
	actions := []mgr.RecoveryAction{
		{Type: mgr.ServiceRestart, Delay: 5 * time.Second},
		{Type: mgr.ServiceRestart, Delay: 15 * time.Second},
		{Type: mgr.ServiceRestart, Delay: time.Minute},
	}
	if err := installed.SetRecoveryActions(actions, 24*60*60); err != nil {
		return fmt.Errorf("configure Vulcan Agent service recovery: %w", err)
	}
	return installed.SetRecoveryActionsOnNonCrashFailures(true)
}

func Uninstall() error {
	manager, err := mgr.Connect()
	if err != nil {
		return err
	}
	defer manager.Disconnect()
	installed, err := manager.OpenService(Name)
	if err != nil {
		return errors.New("Vulcan Agent service is not installed")
	}
	defer installed.Close()
	_, _ = installed.Control(svc.Stop)
	time.Sleep(500 * time.Millisecond)
	return installed.Delete()
}

func ProtectData(path string) error {
	if path == "" {
		return errors.New("Vulcan Agent data path is required")
	}
	command := exec.Command(
		"icacls.exe",
		path,
		"/inheritance:r",
		"/grant:r",
		"*S-1-5-18:(OI)(CI)F",
		"*S-1-5-19:(OI)(CI)F",
		"*S-1-5-32-544:(OI)(CI)F",
	)
	output, err := command.CombinedOutput()
	if err != nil {
		return fmt.Errorf("protect ProgramData ACL: %w: %s", err, string(output))
	}
	return nil
}
