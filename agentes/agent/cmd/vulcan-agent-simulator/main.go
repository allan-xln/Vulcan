package main

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
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	"github.com/lanfuture/vulcan/agentes/agent/internal/transport"
)

const simulatorVersion = "0.2.0"

type enrollmentTokenResponse struct {
	Token string `json:"token"`
}

type simulationResult struct {
	Requested int      `json:"requested"`
	Enrolled  int64    `json:"enrolled"`
	Events    int64    `json:"events"`
	Failed    int64    `json:"failed"`
	Errors    []string `json:"errors,omitempty"`
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "vulcan-agent-simulator:", err)
		os.Exit(1)
	}
}

func run() error {
	serverURL := flag.String("server", "", "Vulcan API URL")
	tenantID := flag.String("tenant", "", "tenant UUID")
	adminToken := flag.String("admin-token", os.Getenv("VULCAN_ADMIN_TOKEN"), "admin bearer token")
	count := flag.Int("agents", 10, "agent count: 10, 100 or 1000")
	eventsPerAgent := flag.Int("events", 3, "simulated events per agent")
	concurrency := flag.Int("concurrency", 10, "parallel enrollment workers")
	profile := flag.String("profile", "workstation", "workstation, server or collector")
	confirm := flag.Bool("confirm-simulated-data", false, "confirm creation of persistent simulated records")
	allowNonLoopback := flag.Bool("allow-non-loopback", false, "explicitly permit a non-loopback test environment")
	flag.Parse()

	if *serverURL == "" || *tenantID == "" || *adminToken == "" {
		return errors.New("--server, --tenant and VULCAN_ADMIN_TOKEN (or --admin-token) are required")
	}
	if !*confirm {
		return errors.New("--confirm-simulated-data is required")
	}
	if *count != 10 && *count != 100 && *count != 1000 {
		return errors.New("--agents must be 10, 100 or 1000")
	}
	if *eventsPerAgent < 1 || *eventsPerAgent > 100 {
		return errors.New("--events must be between 1 and 100")
	}
	if *concurrency < 1 || *concurrency > 50 {
		return errors.New("--concurrency must be between 1 and 50")
	}
	agentProfile := contracts.Profile(*profile)
	if !agentProfile.Valid() {
		return errors.New("--profile must be workstation, server or collector")
	}
	parsed, err := url.Parse(*serverURL)
	if err != nil || parsed.Hostname() == "" {
		return errors.New("invalid --server URL")
	}
	loopback := parsed.Hostname() == "localhost" || parsed.Hostname() == "127.0.0.1" || parsed.Hostname() == "::1"
	if parsed.Scheme != "https" && !(parsed.Scheme == "http" && loopback) {
		return errors.New("HTTPS is mandatory outside loopback")
	}
	if !loopback && !*allowNonLoopback {
		return errors.New("--allow-non-loopback is required outside a local test environment")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()
	tasks := make(chan int)
	failures := make(chan string, *count)
	var enrolled atomic.Int64
	var sentEvents atomic.Int64
	var waitGroup sync.WaitGroup
	httpClient := &http.Client{Timeout: 30 * time.Second}

	for worker := 0; worker < *concurrency; worker++ {
		waitGroup.Add(1)
		go func() {
			defer waitGroup.Done()
			for index := range tasks {
				eventCount, simulationErr := simulateAgent(
					ctx,
					httpClient,
					strings.TrimRight(*serverURL, "/"),
					*tenantID,
					*adminToken,
					agentProfile,
					index,
					*eventsPerAgent,
				)
				if simulationErr != nil {
					failures <- fmt.Sprintf("agent %d: %v", index, simulationErr)
					continue
				}
				enrolled.Add(1)
				sentEvents.Add(int64(eventCount))
			}
		}()
	}
	for index := 1; index <= *count; index++ {
		tasks <- index
	}
	close(tasks)
	waitGroup.Wait()
	close(failures)

	result := simulationResult{
		Requested: *count,
		Enrolled:  enrolled.Load(),
		Events:    sentEvents.Load(),
		Failed:    int64(*count) - enrolled.Load(),
	}
	for failure := range failures {
		if len(result.Errors) < 20 {
			result.Errors = append(result.Errors, failure)
		}
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(result); err != nil {
		return err
	}
	if result.Failed > 0 {
		return fmt.Errorf("%d simulated agents failed", result.Failed)
	}
	return nil
}

func simulateAgent(
	ctx context.Context,
	httpClient *http.Client,
	serverURL string,
	tenantID string,
	adminToken string,
	profile contracts.Profile,
	index int,
	eventsPerAgent int,
) (int, error) {
	token, err := createEnrollmentToken(ctx, httpClient, serverURL, tenantID, adminToken, profile)
	if err != nil {
		return 0, err
	}
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return 0, err
	}
	publicHash := sha256.Sum256(publicKey)
	hostname := fmt.Sprintf("SIM-%s-%04d", strings.ToUpper(string(profile)), index)
	client, err := transport.New(serverURL, "", privateKey, simulatorVersion+"-simulator")
	if err != nil {
		return 0, err
	}
	enrollment, err := client.Enroll(ctx, contracts.EnrollmentRequest{
		EnrollmentToken:      token,
		PublicKey:            base64.StdEncoding.EncodeToString(publicKey),
		PublicKeyFingerprint: hex.EncodeToString(publicHash[:]),
		DeviceFingerprint:    simulatorFingerprint(tenantID, profile, index),
		Hostname:             hostname,
		OperatingSystem:      "Vulcan Agent Simulator",
		Architecture:         "virtual",
		AgentVersion:         simulatorVersion + "-simulator",
		Profile:              profile,
		Metadata:             map[string]any{"simulated": true, "scenario": "load"},
	})
	if err != nil {
		return 0, err
	}
	client, err = transport.New(serverURL, enrollment.AgentID, privateKey, simulatorVersion+"-simulator")
	if err != nil {
		return 0, err
	}
	if _, err := client.Heartbeat(ctx, contracts.HeartbeatRequest{
		Status:         "online",
		AgentVersion:   simulatorVersion + "-simulator",
		PolicyRevision: enrollment.Policy.Revision,
		PolicyStatus:   "applied",
		Modules:        map[string]string{"simulation": "enabled"},
		Performance:    map[string]float64{"goHeapBytes": 0, "goroutines": 1},
	}); err != nil {
		return 0, err
	}
	events := make([]contracts.Event, 0, eventsPerAgent)
	for eventIndex := 1; eventIndex <= eventsPerAgent; eventIndex++ {
		events = append(events, contracts.Event{
			EventID:               randomUUID(),
			SchemaVersion:         contracts.EventSchemaVersion,
			EventType:             "simulation.agent.metric",
			Category:              "simulation",
			Severity:              "info",
			OccurredAt:            time.Now().UTC(),
			Device:                map[string]any{"hostname": hostname},
			Context:               map[string]any{"scenario": "load", "sequence": eventIndex},
			Metrics:               map[string]any{"cpuPercent": float64((index + eventIndex) % 100)},
			Message:               "Evento simulado do Vulcan Agent para validação de carga.",
			Fingerprint:           fmt.Sprintf("simulation:%s:%d:%d", profile, index, eventIndex),
			PrivacyClassification: "operational",
			RetentionPolicy:       "development",
			Extensions:            map[string]any{"dataOrigin": "simulated", "simulator": true},
		})
	}
	response, err := client.Events(ctx, contracts.EventsRequest{
		BatchID: randomUUID(),
		Events:  events,
	})
	if err != nil {
		return 0, err
	}
	return response.Stored, nil
}

func createEnrollmentToken(
	ctx context.Context,
	httpClient *http.Client,
	serverURL string,
	tenantID string,
	adminToken string,
	profile contracts.Profile,
) (string, error) {
	payload, err := json.Marshal(map[string]any{
		"tenantId":         tenantID,
		"profile":          profile,
		"approvalMode":     "automatic",
		"expiresInMinutes": 15,
		"maxUses":          1,
		"tags":             []string{"simulated", "load-test"},
	})
	if err != nil {
		return "", err
	}
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		serverURL+"/agent/v2/admin/enrollment-tokens",
		bytes.NewReader(payload),
	)
	if err != nil {
		return "", err
	}
	request.Header.Set("Authorization", "Bearer "+adminToken)
	request.Header.Set("X-Tenant-Id", tenantID)
	request.Header.Set("Content-Type", "application/json")
	response, err := httpClient.Do(request)
	if err != nil {
		return "", err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		body, _ := io.ReadAll(io.LimitReader(response.Body, 2048))
		return "", fmt.Errorf("create enrollment token returned %d: %s", response.StatusCode, strings.TrimSpace(string(body)))
	}
	var created enrollmentTokenResponse
	if err := json.NewDecoder(io.LimitReader(response.Body, 1024*1024)).Decode(&created); err != nil {
		return "", err
	}
	if created.Token == "" {
		return "", errors.New("server did not return the one-time token")
	}
	return created.Token, nil
}

func simulatorFingerprint(tenantID string, profile contracts.Profile, index int) string {
	sum := sha256.Sum256([]byte(fmt.Sprintf("%s\x00%s\x00%d", tenantID, profile, index)))
	return hex.EncodeToString(sum[:])
}

func randomUUID() string {
	value := make([]byte, 16)
	if _, err := rand.Read(value); err != nil {
		panic(err)
	}
	value[6] = (value[6] & 0x0f) | 0x40
	value[8] = (value[8] & 0x3f) | 0x80
	encoded := hex.EncodeToString(value)
	return fmt.Sprintf(
		"%s-%s-%s-%s-%s",
		encoded[0:8],
		encoded[8:12],
		encoded[12:16],
		encoded[16:20],
		encoded[20:32],
	)
}
