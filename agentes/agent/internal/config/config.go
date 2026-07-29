package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

type Config struct {
	ServerURL                   string            `json:"serverUrl"`
	Profile                     contracts.Profile `json:"profile"`
	TenantID                    string            `json:"tenantId"`
	DeviceID                    string            `json:"deviceId"`
	AgentID                     string            `json:"agentId"`
	PolicySigningPublicKey      string            `json:"policySigningPublicKey"`
	PolicyRevision              int64             `json:"policyRevision"`
	PolicyStatus                string            `json:"policyStatus"`
	DataDir                     string            `json:"dataDir"`
	LogDir                      string            `json:"logDir"`
	AllowInsecureLoopback       bool              `json:"allowInsecureLoopback"`
	AllowInsecurePrivateNetwork bool              `json:"allowInsecurePrivateNetwork"`
	EnrolledAt                  time.Time         `json:"enrolledAt"`
}

type Paths struct {
	ConfigDir string
	DataDir   string
	LogDir    string
}

func DefaultPaths() Paths {
	if runtime.GOOS == "windows" {
		programData := os.Getenv("ProgramData")
		if programData == "" {
			programData = `C:\ProgramData`
		}
		root := filepath.Join(programData, "Vulcan", "Agent")
		return Paths{ConfigDir: root, DataDir: filepath.Join(root, "data"), LogDir: filepath.Join(root, "logs")}
	}
	if isPrivilegedInstall() {
		return Paths{
			ConfigDir: "/etc/vulcan-agent",
			DataDir:   "/var/lib/vulcan-agent",
			LogDir:    "/var/log/vulcan-agent",
		}
	}
	configHome, _ := os.UserConfigDir()
	dataHome := os.Getenv("XDG_STATE_HOME")
	if dataHome == "" {
		home, _ := os.UserHomeDir()
		dataHome = filepath.Join(home, ".local", "state")
	}
	return Paths{
		ConfigDir: filepath.Join(configHome, "vulcan-agent-v2"),
		DataDir:   filepath.Join(dataHome, "vulcan-agent-v2"),
		LogDir:    filepath.Join(dataHome, "vulcan-agent-v2", "logs"),
	}
}

func (paths Paths) Ensure() error {
	for _, path := range []string{paths.ConfigDir, paths.DataDir, paths.LogDir} {
		if err := os.MkdirAll(path, 0o700); err != nil {
			return fmt.Errorf("create protected directory %s: %w", path, err)
		}
		if err := os.Chmod(path, 0o700); err != nil && runtime.GOOS != "windows" {
			return fmt.Errorf("protect directory %s: %w", path, err)
		}
	}
	return nil
}

func (paths Paths) ConfigFile() string {
	return filepath.Join(paths.ConfigDir, "config.json")
}

func Load(paths Paths) (Config, error) {
	data, err := os.ReadFile(paths.ConfigFile())
	if err != nil {
		return Config{}, err
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, fmt.Errorf("decode config: %w", err)
	}
	if err := cfg.Validate(); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func Save(paths Paths, cfg Config) error {
	if err := paths.Ensure(); err != nil {
		return err
	}
	cfg.DataDir = paths.DataDir
	cfg.LogDir = paths.LogDir
	if err := cfg.Validate(); err != nil {
		return err
	}
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	temporary, err := os.CreateTemp(paths.ConfigDir, ".config-*.json")
	if err != nil {
		return err
	}
	temporaryName := temporary.Name()
	defer os.Remove(temporaryName)
	if err := temporary.Chmod(0o600); err != nil {
		temporary.Close()
		return err
	}
	if _, err := temporary.Write(append(data, '\n')); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Sync(); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	return os.Rename(temporaryName, paths.ConfigFile())
}

func (cfg Config) Validate() error {
	if !cfg.Profile.Valid() {
		return errors.New("invalid agent profile")
	}
	if cfg.ServerURL == "" {
		return errors.New("server URL is required")
	}
	parsed, err := url.Parse(cfg.ServerURL)
	if err != nil {
		return fmt.Errorf("invalid server URL: %w", err)
	}
	if parsed.Scheme == "https" {
		return nil
	}
	loopback := parsed.Scheme == "http" &&
		(parsed.Hostname() == "localhost" || net.ParseIP(parsed.Hostname()) != nil && net.ParseIP(parsed.Hostname()).IsLoopback())
	privateAddress := net.ParseIP(parsed.Hostname())
	privateHTTP := parsed.Scheme == "http" && privateAddress != nil && privateAddress.IsPrivate()
	if loopback && cfg.AllowInsecureLoopback {
		return nil
	}
	if privateHTTP && cfg.AllowInsecurePrivateNetwork {
		return nil
	}
	return errors.New("HTTPS is mandatory outside explicit loopback or private-network enrollment")
}
