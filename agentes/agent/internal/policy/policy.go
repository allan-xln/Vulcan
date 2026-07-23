package policy

import (
	"bytes"
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

type Effective struct {
	Revision int64
	Document map[string]any
}

type Store struct {
	dataDir          string
	signingPublicKey ed25519.PublicKey
	agentID          string
	tenantID         string
	profile          contracts.Profile
}

func NewStore(
	dataDir string,
	signingPublicKeyBase64 string,
	tenantID string,
	agentID string,
	profile contracts.Profile,
) (*Store, error) {
	publicKey, err := base64.StdEncoding.DecodeString(signingPublicKeyBase64)
	if err != nil || len(publicKey) != ed25519.PublicKeySize {
		return nil, errors.New("invalid policy signing public key")
	}
	return &Store{
		dataDir:          dataDir,
		signingPublicKey: ed25519.PublicKey(publicKey),
		agentID:          agentID,
		tenantID:         tenantID,
		profile:          profile,
	}, nil
}

func (store *Store) Verify(envelope contracts.SignedPolicyEnvelope) (Effective, error) {
	if envelope.SignatureAlgorithm != "Ed25519" || envelope.SchemaVersion != "v1" {
		return Effective{}, errors.New("unsupported policy signature or schema")
	}
	if envelope.AgentID != store.agentID || envelope.TenantID != store.tenantID {
		return Effective{}, errors.New("policy identity scope mismatch")
	}
	if _, err := time.Parse(time.RFC3339Nano, envelope.IssuedAt); err != nil {
		return Effective{}, errors.New("invalid policy issuedAt")
	}
	signature, err := base64.StdEncoding.DecodeString(envelope.Signature)
	if err != nil {
		return Effective{}, errors.New("invalid policy signature encoding")
	}
	payload := map[string]any{
		"schemaVersion": envelope.SchemaVersion,
		"tenantId":      envelope.TenantID,
		"agentId":       envelope.AgentID,
		"revision":      envelope.Revision,
		"issuedAt":      envelope.IssuedAt,
		"policy":        envelope.Policy,
	}
	canonical, err := canonicalJSON(payload)
	if err != nil {
		return Effective{}, err
	}
	if !ed25519.Verify(store.signingPublicKey, canonical, signature) {
		return Effective{}, errors.New("invalid policy signature")
	}
	if err := validate(envelope.Policy, store.profile); err != nil {
		return Effective{}, err
	}
	return Effective{Revision: envelope.Revision, Document: envelope.Policy}, nil
}

func (store *Store) Apply(envelope contracts.SignedPolicyEnvelope) (Effective, error) {
	effective, err := store.Verify(envelope)
	if err != nil {
		return Effective{}, err
	}
	if err := os.MkdirAll(store.dataDir, 0o700); err != nil {
		return Effective{}, err
	}
	currentPath := filepath.Join(store.dataDir, "policy-current.json")
	previousPath := filepath.Join(store.dataDir, "policy-previous.json")
	if current, readErr := os.ReadFile(currentPath); readErr == nil {
		if err := writeProtected(previousPath, current); err != nil {
			return Effective{}, fmt.Errorf("save policy rollback: %w", err)
		}
	}
	data, err := json.MarshalIndent(envelope, "", "  ")
	if err != nil {
		return Effective{}, err
	}
	if err := writeProtected(currentPath, append(data, '\n')); err != nil {
		return Effective{}, fmt.Errorf("activate policy: %w", err)
	}
	return effective, nil
}

func (store *Store) Load() (Effective, error) {
	data, err := os.ReadFile(filepath.Join(store.dataDir, "policy-current.json"))
	if err != nil {
		return Effective{}, err
	}
	var envelope contracts.SignedPolicyEnvelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		return Effective{}, err
	}
	return store.Verify(envelope)
}

func (store *Store) Rollback() (Effective, error) {
	data, err := os.ReadFile(filepath.Join(store.dataDir, "policy-previous.json"))
	if err != nil {
		return Effective{}, err
	}
	var envelope contracts.SignedPolicyEnvelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		return Effective{}, err
	}
	return store.Apply(envelope)
}

func validate(document map[string]any, profile contracts.Profile) error {
	if value, ok := document["schemaVersion"].(string); ok && value != "v1" {
		return errors.New("unsupported policy schemaVersion")
	}
	if value, ok := document["profile"].(string); ok && value != string(profile) {
		return errors.New("policy profile mismatch")
	}
	modules, _ := document["modules"].(map[string]any)
	for _, name := range []string{"screenCapture", "keylogger", "microphone", "webcam", "remoteShell"} {
		if moduleEnabled(modules, name) {
			return fmt.Errorf("forbidden policy module enabled: %s", name)
		}
	}
	if visual, ok := modules["visual"].(map[string]any); ok {
		screenCapture, _ := visual["screenCapture"].(bool)
		liveSupport, _ := visual["liveSupport"].(bool)
		if screenCapture || liveSupport {
			return errors.New("visual evidence and live support remain disabled in this release")
		}
	}
	if profile != contracts.ProfileWorkstation && moduleEnabled(modules, "activity") {
		return errors.New("activity module is restricted to workstation profile")
	}
	if intervals, ok := document["intervals"].(map[string]any); ok {
		names := make([]string, 0, len(intervals))
		for name := range intervals {
			names = append(names, name)
		}
		sort.Strings(names)
		for _, name := range names {
			seconds, ok := number(intervals[name])
			if !ok || seconds < 5 || seconds > 604800 {
				return fmt.Errorf("invalid interval %s", name)
			}
		}
	}
	if queue, ok := document["queue"].(map[string]any); ok {
		queueLimits := map[string][2]int64{
			"maxEvents":      {100, 1_000_000},
			"maxBytes":       {1_048_576, 10_737_418_240},
			"retentionHours": {1, 720},
			"batchSize":      {1, 500},
		}
		for name, bounds := range queueLimits {
			value, exists := queue[name]
			if !exists {
				continue
			}
			numeric, valid := number(value)
			if !valid || numeric < bounds[0] || numeric > bounds[1] {
				return fmt.Errorf("invalid queue setting %s", name)
			}
		}
	}
	return nil
}

func canonicalJSON(value any) ([]byte, error) {
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		return nil, err
	}
	return bytes.TrimSuffix(buffer.Bytes(), []byte{'\n'}), nil
}

func ModuleEnabled(document map[string]any, name string) bool {
	modules, _ := document["modules"].(map[string]any)
	return moduleEnabled(modules, name)
}

func moduleEnabled(modules map[string]any, name string) bool {
	module, _ := modules[name].(map[string]any)
	enabled, _ := module["enabled"].(bool)
	return enabled
}

func Module(document map[string]any, name string) map[string]any {
	modules, _ := document["modules"].(map[string]any)
	module, _ := modules[name].(map[string]any)
	if module == nil {
		return map[string]any{}
	}
	return module
}

func Interval(document map[string]any, name string, fallback time.Duration) time.Duration {
	intervals, _ := document["intervals"].(map[string]any)
	seconds, ok := number(intervals[name])
	if !ok {
		return fallback
	}
	return time.Duration(seconds) * time.Second
}

func number(value any) (int64, bool) {
	switch typed := value.(type) {
	case float64:
		return int64(typed), typed == float64(int64(typed))
	case int:
		return int64(typed), true
	case int64:
		return typed, true
	case json.Number:
		value, err := typed.Int64()
		return value, err == nil
	default:
		return 0, false
	}
}

func writeProtected(path string, data []byte) error {
	temporary, err := os.CreateTemp(filepath.Dir(path), ".policy-*")
	if err != nil {
		return err
	}
	name := temporary.Name()
	defer os.Remove(name)
	if err := temporary.Chmod(0o600); err != nil && runtime.GOOS != "windows" {
		temporary.Close()
		return err
	}
	if _, err := temporary.Write(data); err != nil {
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
	return os.Rename(name, path)
}
