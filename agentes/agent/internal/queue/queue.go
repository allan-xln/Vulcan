package queue

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/lanfuture/vulcan/agentes/agent/internal/contracts"
	_ "modernc.org/sqlite"
)

const (
	PriorityCritical     = 1
	PriorityAudit        = 2
	PrioritySession      = 3
	PriorityHealth       = 4
	PriorityProductivity = 5
	PriorityMetrics      = 6
)

type Limits struct {
	MaxEvents int
	MaxBytes  int64
	Retention time.Duration
}

type Stats struct {
	Depth          int   `json:"depth"`
	EncryptedBytes int64 `json:"encryptedBytes"`
	OldestAge      int64 `json:"oldestAgeSeconds"`
}

type Item struct {
	ID       string
	Priority int
	Event    contracts.Event
	Attempts int
}

type Queue struct {
	db     *sql.DB
	aead   cipher.AEAD
	limits Limits
}

func Open(dataDir string, limits Limits) (*Queue, error) {
	if limits.MaxEvents <= 0 {
		limits.MaxEvents = 10000
	}
	if limits.MaxBytes <= 0 {
		limits.MaxBytes = 100 * 1024 * 1024
	}
	if limits.Retention <= 0 {
		limits.Retention = 7 * 24 * time.Hour
	}
	if err := os.MkdirAll(dataDir, 0o700); err != nil {
		return nil, err
	}
	key, err := loadOrCreateKey(filepath.Join(dataDir, "queue.key"))
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	aead, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	databasePath := filepath.Join(dataDir, "queue.db")
	db, err := sql.Open("sqlite", databasePath+"?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=synchronous(FULL)")
	if err != nil {
		return nil, err
	}
	statements := []string{
		`create table if not exists queue_events (
			id text primary key,
			priority integer not null check (priority between 1 and 6),
			occurred_at integer not null,
			created_at integer not null,
			attempts integer not null default 0,
			next_attempt_at integer not null default 0,
			payload blob not null,
			payload_size integer not null
		)`,
		`create index if not exists idx_queue_delivery
			on queue_events (priority, occurred_at)`,
		`create index if not exists idx_queue_retry
			on queue_events (next_attempt_at, priority, occurred_at)`,
	}
	for _, statement := range statements {
		if _, err := db.Exec(statement); err != nil {
			db.Close()
			return nil, err
		}
	}
	if runtime.GOOS != "windows" {
		if err := os.Chmod(databasePath, 0o600); err != nil {
			db.Close()
			return nil, fmt.Errorf("protect offline queue: %w", err)
		}
	}
	return &Queue{db: db, aead: aead, limits: limits}, nil
}

func (queue *Queue) Close() error {
	return queue.db.Close()
}

func (queue *Queue) Enqueue(ctx context.Context, event contracts.Event, priority int) error {
	if event.EventID == "" {
		return errors.New("event ID is required")
	}
	if priority < PriorityCritical || priority > PriorityMetrics {
		return errors.New("invalid queue priority")
	}
	data, err := json.Marshal(event)
	if err != nil {
		return err
	}
	encrypted, err := queue.encrypt(data)
	if err != nil {
		return err
	}
	transaction, err := queue.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer transaction.Rollback()
	if _, err := transaction.ExecContext(
		ctx,
		`delete from queue_events
		 where priority > 2 and created_at < ?`,
		time.Now().Add(-queue.limits.Retention).UnixNano(),
	); err != nil {
		return err
	}
	_, err = transaction.ExecContext(
		ctx,
		`insert or ignore into queue_events
			(id, priority, occurred_at, created_at, payload, payload_size)
		 values (?, ?, ?, ?, ?, ?)`,
		event.EventID,
		priority,
		event.OccurredAt.UnixNano(),
		time.Now().UnixNano(),
		encrypted,
		len(encrypted),
	)
	if err != nil {
		return err
	}
	if err := queue.enforceLimits(ctx, transaction); err != nil {
		return err
	}
	return transaction.Commit()
}

func (queue *Queue) enforceLimits(ctx context.Context, transaction *sql.Tx) error {
	for {
		var count int
		var size int64
		if err := transaction.QueryRowContext(
			ctx,
			`select count(*), coalesce(sum(payload_size), 0) from queue_events`,
		).Scan(&count, &size); err != nil {
			return err
		}
		if count <= queue.limits.MaxEvents && size <= queue.limits.MaxBytes {
			return nil
		}
		result, err := transaction.ExecContext(
			ctx,
			`delete from queue_events where id = (
				select id from queue_events
				where priority > 2
				order by priority desc, occurred_at, created_at
				limit 1
			)`,
		)
		if err != nil {
			return err
		}
		removed, _ := result.RowsAffected()
		if removed == 0 {
			return errors.New("offline queue capacity is exhausted by protected critical/audit events")
		}
	}
}

func (queue *Queue) Peek(ctx context.Context, limit int) ([]Item, error) {
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	rows, err := queue.db.QueryContext(
		ctx,
		`select id, priority, payload, attempts
		 from queue_events
		 where next_attempt_at <= ?
		 order by priority, occurred_at, created_at
		 limit ?`,
		time.Now().Unix(),
		limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]Item, 0, limit)
	for rows.Next() {
		var item Item
		var encrypted []byte
		if err := rows.Scan(&item.ID, &item.Priority, &encrypted, &item.Attempts); err != nil {
			return nil, err
		}
		data, err := queue.decrypt(encrypted)
		if err != nil {
			return nil, fmt.Errorf("decrypt queued event %s: %w", item.ID, err)
		}
		if err := json.Unmarshal(data, &item.Event); err != nil {
			return nil, fmt.Errorf("decode queued event %s: %w", item.ID, err)
		}
		item.Event.OfflineBuffered = item.Attempts > 0
		items = append(items, item)
	}
	return items, rows.Err()
}

func (queue *Queue) Ack(ctx context.Context, ids []string) error {
	if len(ids) == 0 {
		return nil
	}
	transaction, err := queue.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer transaction.Rollback()
	for _, id := range ids {
		if _, err := transaction.ExecContext(ctx, `delete from queue_events where id = ?`, id); err != nil {
			return err
		}
	}
	return transaction.Commit()
}

func (queue *Queue) Fail(ctx context.Context, ids []string) error {
	if len(ids) == 0 {
		return nil
	}
	transaction, err := queue.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer transaction.Rollback()
	for _, id := range ids {
		var attempts int
		if err := transaction.QueryRowContext(ctx, `select attempts from queue_events where id = ?`, id).Scan(&attempts); err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				continue
			}
			return err
		}
		attempts++
		backoff := time.Second << min(attempts, 8)
		if backoff > 5*time.Minute {
			backoff = 5 * time.Minute
		}
		jitter := time.Duration(time.Now().UnixNano()%int64(time.Second)) / 2
		if _, err := transaction.ExecContext(
			ctx,
			`update queue_events
			 set attempts = ?, next_attempt_at = ?
			 where id = ?`,
			attempts,
			time.Now().Add(backoff+jitter).Unix(),
			id,
		); err != nil {
			return err
		}
	}
	return transaction.Commit()
}

func (queue *Queue) Stats(ctx context.Context) (Stats, error) {
	var stats Stats
	var oldest sql.NullInt64
	err := queue.db.QueryRowContext(
		ctx,
		`select count(*), coalesce(sum(payload_size), 0), min(created_at) from queue_events`,
	).Scan(&stats.Depth, &stats.EncryptedBytes, &oldest)
	if err != nil {
		return Stats{}, err
	}
	if oldest.Valid {
		stats.OldestAge = max(0, (time.Now().UnixNano()-oldest.Int64)/int64(time.Second))
	}
	return stats, nil
}

func (queue *Queue) encrypt(plaintext []byte) ([]byte, error) {
	nonce := make([]byte, queue.aead.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	return append(nonce, queue.aead.Seal(nil, nonce, plaintext, nil)...), nil
}

func (queue *Queue) decrypt(ciphertext []byte) ([]byte, error) {
	if len(ciphertext) < queue.aead.NonceSize() {
		return nil, errors.New("encrypted queue payload is truncated")
	}
	return queue.aead.Open(
		nil,
		ciphertext[:queue.aead.NonceSize()],
		ciphertext[queue.aead.NonceSize():],
		nil,
	)
}

func loadOrCreateKey(path string) ([]byte, error) {
	if data, err := os.ReadFile(path); err == nil {
		if len(data) != 32 {
			return nil, errors.New("invalid queue encryption key")
		}
		return data, nil
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		return nil, err
	}
	file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return nil, err
	}
	if _, err := file.Write(key); err != nil {
		file.Close()
		return nil, err
	}
	if err := file.Sync(); err != nil {
		file.Close()
		return nil, err
	}
	return key, file.Close()
}

func IntegrityCheck(ctx context.Context, databasePath string) error {
	if strings.TrimSpace(databasePath) == "" {
		return errors.New("database path is required")
	}
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		return err
	}
	defer db.Close()
	var result string
	if err := db.QueryRowContext(ctx, "pragma integrity_check").Scan(&result); err != nil {
		return err
	}
	if result != "ok" {
		return fmt.Errorf("SQLite integrity check failed: %s", result)
	}
	return nil
}
