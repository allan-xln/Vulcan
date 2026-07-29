package transport

import (
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

func TestPrivateHTTPRequiresExplicitOption(t *testing.T) {
	_, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := New("http://192.168.200.4:8099/api", "", privateKey, "test"); err == nil {
		t.Fatal("private HTTP was accepted without explicit option")
	}
	if _, err := New(
		"http://192.168.200.4:8099/api",
		"",
		privateKey,
		"test",
		WithInsecurePrivateNetwork(),
	); err != nil {
		t.Fatalf("explicit private HTTP was rejected: %v", err)
	}
	if _, err := New(
		"http://203.0.113.10/api",
		"",
		privateKey,
		"test",
		WithInsecurePrivateNetwork(),
	); err == nil {
		t.Fatal("public HTTP was accepted with private-network option")
	}
}

func TestSignedHeartbeatRequestCanBeVerifiedByGatewayContract(t *testing.T) {
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	agentID := "00000000-0000-0000-0000-000000000501"
	server := httptest.NewServer(http.HandlerFunc(func(response http.ResponseWriter, request *http.Request) {
		body, readErr := io.ReadAll(request.Body)
		if readErr != nil {
			t.Error(readErr)
			response.WriteHeader(http.StatusInternalServerError)
			return
		}
		bodyHash := sha256.Sum256(body)
		if request.Header.Get("X-Vulcan-Content-SHA256") != hex.EncodeToString(bodyHash[:]) {
			t.Error("body hash header mismatch")
		}
		signature, decodeErr := base64.StdEncoding.DecodeString(request.Header.Get("X-Vulcan-Signature"))
		if decodeErr != nil {
			t.Error(decodeErr)
		}
		signingPayload := strings.Join([]string{
			request.Method,
			request.URL.Path,
			request.Header.Get("X-Vulcan-Timestamp"),
			request.Header.Get("X-Vulcan-Nonce"),
			request.Header.Get("X-Vulcan-Content-SHA256"),
		}, "\n")
		if !ed25519.Verify(publicKey, []byte(signingPayload), signature) {
			t.Error("request signature is invalid")
		}
		response.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(response).Encode(contracts.HeartbeatResponse{
			Accepted: true,
			Commands: []contracts.Command{},
		})
	}))
	defer server.Close()

	client, err := New(server.URL, agentID, privateKey, "test")
	if err != nil {
		t.Fatal(err)
	}
	result, err := client.Heartbeat(context.Background(), contracts.HeartbeatRequest{
		Status:       "online",
		AgentVersion: "test",
		Modules:      map[string]string{},
		Performance:  map[string]float64{},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !result.Accepted {
		t.Fatal("heartbeat response was not accepted")
	}
}
