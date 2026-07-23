package policy

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"testing"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

func signedEnvelope(
	t *testing.T,
	privateKey ed25519.PrivateKey,
	revision int64,
	document map[string]any,
) contracts.SignedPolicyEnvelope {
	t.Helper()
	envelope := contracts.SignedPolicyEnvelope{
		SchemaVersion:      "v1",
		TenantID:           "00000000-0000-0000-0000-000000000301",
		AgentID:            "00000000-0000-0000-0000-000000000501",
		Revision:           revision,
		IssuedAt:           time.Now().UTC().Format(time.RFC3339Nano),
		Policy:             document,
		SignatureAlgorithm: "Ed25519",
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
		t.Fatal(err)
	}
	envelope.Signature = base64.StdEncoding.EncodeToString(ed25519.Sign(privateKey, canonical))
	return envelope
}

func safePolicy(profile string) map[string]any {
	return map[string]any{
		"schemaVersion": "v1",
		"profile":       profile,
		"modules": map[string]any{
			"activity": map[string]any{"enabled": profile == "workstation"},
			"visual":   map[string]any{"screenCapture": false, "liveSupport": false},
		},
		"intervals": map[string]any{"sync": 30},
	}
}

func TestSignedPolicyApplyAndRollback(t *testing.T) {
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	store, err := NewStore(
		t.TempDir(),
		base64.StdEncoding.EncodeToString(publicKey),
		"00000000-0000-0000-0000-000000000301",
		"00000000-0000-0000-0000-000000000501",
		contracts.ProfileWorkstation,
	)
	if err != nil {
		t.Fatal(err)
	}
	first := signedEnvelope(t, privateKey, 1, safePolicy("workstation"))
	if _, err := store.Apply(first); err != nil {
		t.Fatal(err)
	}
	secondDocument := safePolicy("workstation")
	secondDocument["intervals"] = map[string]any{"sync": 60}
	second := signedEnvelope(t, privateKey, 2, secondDocument)
	if _, err := store.Apply(second); err != nil {
		t.Fatal(err)
	}
	rolledBack, err := store.Rollback()
	if err != nil {
		t.Fatal(err)
	}
	if rolledBack.Revision != 1 {
		t.Fatalf("rollback loaded revision %d, expected 1", rolledBack.Revision)
	}
}

func TestPolicyRejectsTamperingAndVisualCapture(t *testing.T) {
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	store, err := NewStore(
		t.TempDir(),
		base64.StdEncoding.EncodeToString(publicKey),
		"00000000-0000-0000-0000-000000000301",
		"00000000-0000-0000-0000-000000000501",
		contracts.ProfileWorkstation,
	)
	if err != nil {
		t.Fatal(err)
	}
	tampered := signedEnvelope(t, privateKey, 1, safePolicy("workstation"))
	tampered.Policy["intervals"] = map[string]any{"sync": 5}
	if _, err := store.Verify(tampered); err == nil {
		t.Fatal("tampered policy signature was accepted")
	}
	invasive := safePolicy("workstation")
	invasive["modules"].(map[string]any)["visual"] = map[string]any{"screenCapture": true}
	invasiveEnvelope := signedEnvelope(t, privateKey, 2, invasive)
	if _, err := store.Verify(invasiveEnvelope); err == nil {
		t.Fatal("visual capture policy was accepted")
	}
}
