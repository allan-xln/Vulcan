package config

import (
	"testing"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

func TestPrivateHTTPConfigurationRequiresExplicitConsent(t *testing.T) {
	base := Config{
		ServerURL: "http://192.168.200.4:8099/api",
		Profile:   contracts.ProfileWorkstation,
	}
	if err := base.Validate(); err == nil {
		t.Fatal("private HTTP configuration was accepted without explicit consent")
	}
	base.AllowInsecurePrivateNetwork = true
	if err := base.Validate(); err != nil {
		t.Fatalf("explicit private HTTP configuration was rejected: %v", err)
	}
	base.ServerURL = "http://203.0.113.10/api"
	if err := base.Validate(); err == nil {
		t.Fatal("public HTTP configuration was accepted with private-network consent")
	}
}
