package transport

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

const maximumErrorBody = 4096

type Client struct {
	serverURL  string
	agentID    string
	privateKey ed25519.PrivateKey
	httpClient *http.Client
	userAgent  string

	mu          sync.Mutex
	failures    int
	circuitOpen time.Time
}

func New(serverURL, agentID string, privateKey ed25519.PrivateKey, version string) (*Client, error) {
	parsed, err := url.Parse(serverURL)
	if err != nil {
		return nil, fmt.Errorf("parse server URL: %w", err)
	}
	if parsed.Scheme != "https" && !(parsed.Scheme == "http" && isLoopback(parsed.Hostname())) {
		return nil, errors.New("Vulcan Agent requires HTTPS outside loopback development")
	}
	return &Client{
		serverURL:  strings.TrimRight(serverURL, "/"),
		agentID:    agentID,
		privateKey: privateKey,
		httpClient: &http.Client{Timeout: 30 * time.Second},
		userAgent:  "Vulcan-Agent/" + version,
	}, nil
}

func (client *Client) TestConnection(ctx context.Context) error {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, client.serverURL+"/agent/v2/status", nil)
	if err != nil {
		return err
	}
	request.Header.Set("User-Agent", client.userAgent)
	response, err := client.httpClient.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return responseError(response)
	}
	return nil
}

func (client *Client) Enroll(
	ctx context.Context,
	request contracts.EnrollmentRequest,
) (contracts.EnrollmentResponse, error) {
	var response contracts.EnrollmentResponse
	err := client.doUnsigned(ctx, http.MethodPost, "/agent/v2/enroll", request, &response)
	return response, err
}

func (client *Client) Heartbeat(
	ctx context.Context,
	request contracts.HeartbeatRequest,
) (contracts.HeartbeatResponse, error) {
	var response contracts.HeartbeatResponse
	err := client.doSigned(ctx, http.MethodPost, "/agent/v2/heartbeat", request, &response)
	return response, err
}

func (client *Client) Events(
	ctx context.Context,
	request contracts.EventsRequest,
) (contracts.EventsResponse, error) {
	var response contracts.EventsResponse
	err := client.doSigned(ctx, http.MethodPost, "/agent/v2/events", request, &response)
	return response, err
}

func (client *Client) Policy(ctx context.Context) (contracts.SignedPolicyEnvelope, error) {
	var response contracts.SignedPolicyEnvelope
	err := client.doSigned(ctx, http.MethodGet, "/agent/v2/policy", nil, &response)
	return response, err
}

func (client *Client) CommandResult(
	ctx context.Context,
	commandID string,
	status string,
	outputSummary string,
) error {
	payload := map[string]any{"status": status}
	if outputSummary != "" {
		payload["outputSummary"] = outputSummary
	}
	return client.doSigned(
		ctx,
		http.MethodPost,
		"/agent/v2/commands/"+url.PathEscape(commandID)+"/result",
		payload,
		nil,
	)
}

func (client *Client) Unenroll(ctx context.Context, reason string) error {
	return client.doSigned(
		ctx,
		http.MethodPost,
		"/agent/v2/unenroll",
		map[string]string{"reason": reason},
		nil,
	)
}

func (client *Client) doUnsigned(
	ctx context.Context,
	method string,
	path string,
	payload any,
	result any,
) error {
	body, err := marshalPayload(payload)
	if err != nil {
		return err
	}
	var lastError error
	for attempt := 0; attempt < 3; attempt++ {
		request, err := http.NewRequestWithContext(
			ctx,
			method,
			client.serverURL+path,
			bytes.NewReader(body),
		)
		if err != nil {
			return err
		}
		request.Header.Set("Content-Type", "application/json")
		request.Header.Set("User-Agent", client.userAgent)
		response, err := client.httpClient.Do(request)
		if err == nil {
			defer response.Body.Close()
			if response.StatusCode >= 200 && response.StatusCode < 300 {
				return decodeResponse(response, result)
			}
			lastError = responseError(response)
			if response.StatusCode < 500 && response.StatusCode != http.StatusTooManyRequests {
				return lastError
			}
		} else {
			lastError = err
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(time.Duration(attempt+1)*time.Second + randomJitter()):
		}
	}
	return lastError
}

func (client *Client) doSigned(
	ctx context.Context,
	method string,
	path string,
	payload any,
	result any,
) error {
	if client.agentID == "" || len(client.privateKey) != ed25519.PrivateKeySize {
		return errors.New("signed transport requires an enrolled agent identity")
	}
	if err := client.beforeRequest(); err != nil {
		return err
	}
	body, err := marshalPayload(payload)
	if err != nil {
		return err
	}
	timestamp := fmt.Sprintf("%d", time.Now().Unix())
	nonce, err := randomToken(24)
	if err != nil {
		return err
	}
	bodyHash := sha256.Sum256(body)
	bodyHashHex := hex.EncodeToString(bodyHash[:])
	signingPayload := strings.Join([]string{method, path, timestamp, nonce, bodyHashHex}, "\n")
	signature := ed25519.Sign(client.privateKey, []byte(signingPayload))

	request, err := http.NewRequestWithContext(
		ctx,
		method,
		client.serverURL+path,
		bytes.NewReader(body),
	)
	if err != nil {
		return err
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("User-Agent", client.userAgent)
	request.Header.Set("X-Vulcan-Agent-Id", client.agentID)
	request.Header.Set("X-Vulcan-Timestamp", timestamp)
	request.Header.Set("X-Vulcan-Nonce", nonce)
	request.Header.Set("X-Vulcan-Content-SHA256", bodyHashHex)
	request.Header.Set("X-Vulcan-Signature", base64.StdEncoding.EncodeToString(signature))

	response, err := client.httpClient.Do(request)
	if err != nil {
		client.recordFailure()
		return err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		client.recordFailure()
		return responseError(response)
	}
	client.recordSuccess()
	return decodeResponse(response, result)
}

func marshalPayload(payload any) ([]byte, error) {
	if payload == nil {
		return []byte{}, nil
	}
	return json.Marshal(payload)
}

func decodeResponse(response *http.Response, result any) error {
	if result == nil || response.StatusCode == http.StatusNoContent {
		_, _ = io.Copy(io.Discard, response.Body)
		return nil
	}
	decoder := json.NewDecoder(io.LimitReader(response.Body, 4*1024*1024))
	if err := decoder.Decode(result); err != nil {
		return fmt.Errorf("decode Vulcan response: %w", err)
	}
	return nil
}

func responseError(response *http.Response) error {
	body, _ := io.ReadAll(io.LimitReader(response.Body, maximumErrorBody))
	var problem struct {
		Detail string `json:"detail"`
	}
	if json.Unmarshal(body, &problem) == nil && problem.Detail != "" {
		return fmt.Errorf("Vulcan API returned %d: %s", response.StatusCode, problem.Detail)
	}
	return fmt.Errorf("Vulcan API returned HTTP %d", response.StatusCode)
}

func (client *Client) beforeRequest() error {
	client.mu.Lock()
	defer client.mu.Unlock()
	if time.Now().Before(client.circuitOpen) {
		return fmt.Errorf("transport circuit is open until %s", client.circuitOpen.Format(time.RFC3339))
	}
	return nil
}

func (client *Client) recordFailure() {
	client.mu.Lock()
	defer client.mu.Unlock()
	client.failures++
	if client.failures >= 5 {
		client.circuitOpen = time.Now().Add(30 * time.Second)
	}
}

func (client *Client) recordSuccess() {
	client.mu.Lock()
	defer client.mu.Unlock()
	client.failures = 0
	client.circuitOpen = time.Time{}
}

func randomToken(size int) (string, error) {
	data := make([]byte, size)
	if _, err := rand.Read(data); err != nil {
		return "", err
	}
	return hex.EncodeToString(data), nil
}

func randomJitter() time.Duration {
	data := make([]byte, 1)
	if _, err := rand.Read(data); err != nil {
		return 0
	}
	return time.Duration(data[0]) * time.Millisecond
}

func isLoopback(host string) bool {
	return host == "localhost" || host == "127.0.0.1" || host == "::1"
}
