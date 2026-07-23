package queue

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
)

func testEvent(id, message string) contracts.Event {
	return contracts.Event{
		EventID:               id,
		SchemaVersion:         contracts.EventSchemaVersion,
		EventType:             "agent.test",
		Category:              "health",
		Severity:              "info",
		OccurredAt:            time.Now().UTC(),
		Message:               message,
		Fingerprint:           id,
		PrivacyClassification: "operational",
		RetentionPolicy:       "standard",
	}
}

func TestOfflineQueueEncryptsDeduplicatesReplaysAndAcknowledges(t *testing.T) {
	ctx := context.Background()
	dataDir := t.TempDir()
	eventQueue, err := Open(dataDir, Limits{MaxEvents: 10, MaxBytes: 1024 * 1024})
	if err != nil {
		t.Fatal(err)
	}
	defer eventQueue.Close()

	event := testEvent("00000000-0000-4000-8000-000000000001", "plaintext-marker-that-must-not-leak")
	if err := eventQueue.Enqueue(ctx, event, PriorityHealth); err != nil {
		t.Fatal(err)
	}
	if err := eventQueue.Enqueue(ctx, event, PriorityHealth); err != nil {
		t.Fatal(err)
	}
	stats, err := eventQueue.Stats(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.Depth != 1 {
		t.Fatalf("deduplication failed, depth=%d", stats.Depth)
	}
	database, err := os.ReadFile(filepath.Join(dataDir, "queue.db"))
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(database, []byte(event.Message)) {
		t.Fatal("queue database contains plaintext event payload")
	}
	items, err := eventQueue.Peek(ctx, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || items[0].Event.OfflineBuffered {
		t.Fatalf("unexpected replay batch: %#v", items)
	}
	if err := eventQueue.Fail(ctx, []string{event.EventID}); err != nil {
		t.Fatal(err)
	}
	time.Sleep(3 * time.Second)
	items, err = eventQueue.Peek(ctx, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || !items[0].Event.OfflineBuffered {
		t.Fatalf("failed upload was not marked as offline buffered: %#v", items)
	}
	if err := eventQueue.Ack(ctx, []string{event.EventID}); err != nil {
		t.Fatal(err)
	}
	stats, err = eventQueue.Stats(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.Depth != 0 {
		t.Fatalf("acknowledged event remained queued, depth=%d", stats.Depth)
	}
}

func TestQueueOverflowDropsOldLowPriorityBeforeProtectedEvents(t *testing.T) {
	ctx := context.Background()
	eventQueue, err := Open(t.TempDir(), Limits{MaxEvents: 2, MaxBytes: 1024 * 1024})
	if err != nil {
		t.Fatal(err)
	}
	defer eventQueue.Close()

	critical := testEvent("00000000-0000-4000-8000-000000000010", "critical")
	metricOne := testEvent("00000000-0000-4000-8000-000000000011", "metric-one")
	metricTwo := testEvent("00000000-0000-4000-8000-000000000012", "metric-two")
	if err := eventQueue.Enqueue(ctx, critical, PriorityCritical); err != nil {
		t.Fatal(err)
	}
	if err := eventQueue.Enqueue(ctx, metricOne, PriorityMetrics); err != nil {
		t.Fatal(err)
	}
	if err := eventQueue.Enqueue(ctx, metricTwo, PriorityMetrics); err != nil {
		t.Fatal(err)
	}
	items, err := eventQueue.Peek(ctx, 10)
	if err != nil {
		t.Fatal(err)
	}
	foundCritical := false
	foundOldMetric := false
	for _, item := range items {
		foundCritical = foundCritical || item.ID == critical.EventID
		foundOldMetric = foundOldMetric || item.ID == metricOne.EventID
	}
	if !foundCritical {
		t.Fatal("overflow removed a protected critical event")
	}
	if foundOldMetric {
		t.Fatal("overflow did not remove the oldest low-priority event")
	}
}

func TestQueueRetentionRemovesExpiredLowPriorityButKeepsAudit(t *testing.T) {
	ctx := context.Background()
	eventQueue, err := Open(t.TempDir(), Limits{
		MaxEvents: 10,
		MaxBytes:  1024 * 1024,
		Retention: time.Hour,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer eventQueue.Close()

	metric := testEvent("00000000-0000-4000-8000-000000000020", "expired metric")
	audit := testEvent("00000000-0000-4000-8000-000000000021", "protected audit")
	if err := eventQueue.Enqueue(ctx, metric, PriorityMetrics); err != nil {
		t.Fatal(err)
	}
	if err := eventQueue.Enqueue(ctx, audit, PriorityAudit); err != nil {
		t.Fatal(err)
	}
	if _, err := eventQueue.db.Exec(
		`update queue_events set created_at = ? where id in (?, ?)`,
		time.Now().Add(-2*time.Hour).UnixNano(),
		metric.EventID,
		audit.EventID,
	); err != nil {
		t.Fatal(err)
	}
	trigger := testEvent("00000000-0000-4000-8000-000000000022", "retention trigger")
	if err := eventQueue.Enqueue(ctx, trigger, PriorityHealth); err != nil {
		t.Fatal(err)
	}
	items, err := eventQueue.Peek(ctx, 10)
	if err != nil {
		t.Fatal(err)
	}
	foundMetric := false
	foundAudit := false
	for _, item := range items {
		foundMetric = foundMetric || item.ID == metric.EventID
		foundAudit = foundAudit || item.ID == audit.EventID
	}
	if foundMetric {
		t.Fatal("expired low-priority event survived retention")
	}
	if !foundAudit {
		t.Fatal("retention removed a protected audit event")
	}
}
