package contracts

import (
	"context"
	"encoding/json"
	"time"
)

const EventSchemaVersion = "2026-07-vulcan-event.v1"

type Profile string

const (
	ProfileWorkstation Profile = "workstation"
	ProfileServer      Profile = "server"
	ProfileCollector   Profile = "collector"
)

func (profile Profile) Valid() bool {
	switch profile {
	case ProfileWorkstation, ProfileServer, ProfileCollector:
		return true
	default:
		return false
	}
}

type Event struct {
	EventID               string         `json:"eventId"`
	SchemaVersion         string         `json:"schemaVersion"`
	EventType             string         `json:"eventType"`
	Category              string         `json:"category"`
	Severity              string         `json:"severity"`
	OccurredAt            time.Time      `json:"occurredAt"`
	Actor                 map[string]any `json:"actor,omitempty"`
	Device                map[string]any `json:"device,omitempty"`
	Context               map[string]any `json:"context,omitempty"`
	Metrics               map[string]any `json:"metrics,omitempty"`
	Message               string         `json:"message"`
	TechnicalMessage      string         `json:"technicalMessage,omitempty"`
	Fingerprint           string         `json:"fingerprint"`
	CorrelationID         string         `json:"correlationId,omitempty"`
	CausationID           string         `json:"causationId,omitempty"`
	Confidence            *float64       `json:"confidence,omitempty"`
	PrivacyClassification string         `json:"privacyClassification"`
	RetentionPolicy       string         `json:"retentionPolicy"`
	OfflineBuffered       bool           `json:"offlineBuffered"`
	Extensions            map[string]any `json:"extensions,omitempty"`
}

type SignedPolicyEnvelope struct {
	SchemaVersion      string         `json:"schemaVersion"`
	TenantID           string         `json:"tenantId"`
	AgentID            string         `json:"agentId"`
	Revision           int64          `json:"revision"`
	IssuedAt           string         `json:"issuedAt"`
	Policy             map[string]any `json:"policy"`
	SignatureAlgorithm string         `json:"signatureAlgorithm"`
	Signature          string         `json:"signature"`
}

type EnrollmentRequest struct {
	EnrollmentToken      string         `json:"enrollmentToken"`
	PublicKey            string         `json:"publicKey"`
	PublicKeyFingerprint string         `json:"publicKeyFingerprint"`
	DeviceFingerprint    string         `json:"deviceFingerprint"`
	Hostname             string         `json:"hostname"`
	OperatingSystem      string         `json:"operatingSystem"`
	Architecture         string         `json:"architecture"`
	AgentVersion         string         `json:"agentVersion"`
	Profile              Profile        `json:"profile"`
	Metadata             map[string]any `json:"metadata"`
}

type EnrollmentResponse struct {
	Accepted               bool                 `json:"accepted"`
	TenantID               string               `json:"tenantId"`
	DeviceID               string               `json:"deviceId"`
	AgentID                string               `json:"agentId"`
	Status                 string               `json:"status"`
	ServerTime             time.Time            `json:"serverTime"`
	PolicySigningPublicKey string               `json:"policySigningPublicKey"`
	Policy                 SignedPolicyEnvelope `json:"policy"`
}

type HeartbeatRequest struct {
	Status         string             `json:"status"`
	AgentVersion   string             `json:"agentVersion"`
	QueueDepth     int                `json:"queueDepth"`
	PolicyRevision int64              `json:"policyRevision"`
	PolicyStatus   string             `json:"policyStatus"`
	LocalIP        string             `json:"localIp,omitempty"`
	LastError      string             `json:"lastError,omitempty"`
	Modules        map[string]string  `json:"modules"`
	Performance    map[string]float64 `json:"performance"`
}

type Command struct {
	CommandID   string         `json:"commandId"`
	CommandType string         `json:"commandType"`
	Reason      string         `json:"reason"`
	Payload     map[string]any `json:"payload"`
	ExpiresAt   time.Time      `json:"expiresAt"`
}

type HeartbeatResponse struct {
	Accepted   bool                  `json:"accepted"`
	ServerTime time.Time             `json:"serverTime"`
	Policy     *SignedPolicyEnvelope `json:"policy,omitempty"`
	Commands   []Command             `json:"commands"`
}

type EventsRequest struct {
	BatchID string  `json:"batchId"`
	Events  []Event `json:"events"`
}

type EventsResponse struct {
	Accepted             bool      `json:"accepted"`
	Received             int       `json:"received"`
	Stored               int       `json:"stored"`
	Duplicates           int       `json:"duplicates"`
	AcknowledgedEventIDs []string  `json:"acknowledgedEventIds"`
	ServerTime           time.Time `json:"serverTime"`
}

type Health struct {
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
}

type Emitter interface {
	Emit(context.Context, Event, int) error
}

type Collector interface {
	Name() string
	Profiles() []Profile
	Supported(context.Context) bool
	Configure(map[string]any) error
	Collect(context.Context) ([]Event, error)
	Health(context.Context) Health
}

func EventFromJSON(data []byte) (Event, error) {
	var event Event
	err := json.Unmarshal(data, &event)
	return event, err
}
