package collectors

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

func newEvent(
	eventType string,
	category string,
	severity string,
	message string,
	context map[string]any,
	metrics map[string]any,
) contracts.Event {
	hostname, _ := os.Hostname()
	occurredAt := time.Now().UTC()
	fingerprintInput := fmt.Sprintf("%s:%s:%d", hostname, eventType, occurredAt.Unix()/30)
	fingerprint := sha256.Sum256([]byte(fingerprintInput))
	return contracts.Event{
		EventID:               newUUID(),
		SchemaVersion:         contracts.EventSchemaVersion,
		EventType:             eventType,
		Category:              category,
		Severity:              severity,
		OccurredAt:            occurredAt,
		Device:                map[string]any{"hostname": hostname},
		Context:               context,
		Metrics:               metrics,
		Message:               message,
		Fingerprint:           hex.EncodeToString(fingerprint[:]),
		PrivacyClassification: "operational",
		RetentionPolicy:       "standard",
		Extensions:            map[string]any{"collector": "vulcan-agent"},
	}
}

func newUUID() string {
	data := make([]byte, 16)
	if _, err := rand.Read(data); err != nil {
		fallback := sha256.Sum256([]byte(fmt.Sprintf("%d", time.Now().UnixNano())))
		data = fallback[:16]
	}
	data[6] = (data[6] & 0x0f) | 0x40
	data[8] = (data[8] & 0x3f) | 0x80
	encoded := hex.EncodeToString(data)
	return fmt.Sprintf("%s-%s-%s-%s-%s", encoded[:8], encoded[8:12], encoded[12:16], encoded[16:20], encoded[20:])
}

func profileSupported(profile contracts.Profile, profiles []contracts.Profile) bool {
	for _, supported := range profiles {
		if supported == profile {
			return true
		}
	}
	return false
}
