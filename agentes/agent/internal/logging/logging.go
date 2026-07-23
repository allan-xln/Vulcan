package logging

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type rotatingWriter struct {
	mu       sync.Mutex
	path     string
	file     *os.File
	size     int64
	maxBytes int64
	backups  int
}

func New(logDir string, level slog.Level) (*slog.Logger, io.Closer, error) {
	if err := os.MkdirAll(logDir, 0o700); err != nil {
		return nil, nil, err
	}
	writer := &rotatingWriter{
		path:     filepath.Join(logDir, "agent.jsonl"),
		maxBytes: 5 * 1024 * 1024,
		backups:  5,
	}
	if err := writer.open(); err != nil {
		return nil, nil, err
	}
	handler := slog.NewJSONHandler(writer, &slog.HandlerOptions{Level: level})
	return slog.New(&redactingHandler{next: handler}), writer, nil
}

func (writer *rotatingWriter) Write(data []byte) (int, error) {
	writer.mu.Lock()
	defer writer.mu.Unlock()
	if writer.size+int64(len(data)) > writer.maxBytes {
		if err := writer.rotate(); err != nil {
			return 0, err
		}
	}
	written, err := writer.file.Write(data)
	writer.size += int64(written)
	return written, err
}

func (writer *rotatingWriter) Close() error {
	writer.mu.Lock()
	defer writer.mu.Unlock()
	if writer.file == nil {
		return nil
	}
	return writer.file.Close()
}

func (writer *rotatingWriter) open() error {
	file, err := os.OpenFile(writer.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	info, err := file.Stat()
	if err != nil {
		file.Close()
		return err
	}
	writer.file = file
	writer.size = info.Size()
	return nil
}

func (writer *rotatingWriter) rotate() error {
	if err := writer.file.Close(); err != nil {
		return err
	}
	for index := writer.backups - 1; index >= 1; index-- {
		older := fmt.Sprintf("%s.%d", writer.path, index)
		newer := fmt.Sprintf("%s.%d", writer.path, index+1)
		_ = os.Rename(older, newer)
	}
	_ = os.Rename(writer.path, writer.path+".1")
	return writer.open()
}

type redactingHandler struct {
	next slog.Handler
}

func (handler *redactingHandler) Enabled(ctx context.Context, level slog.Level) bool {
	return handler.next.Enabled(ctx, level)
}

func (handler *redactingHandler) Handle(ctx context.Context, record slog.Record) error {
	redacted := slog.NewRecord(record.Time, record.Level, record.Message, record.PC)
	record.Attrs(func(attribute slog.Attr) bool {
		switch attribute.Key {
		case "token", "enrollmentToken", "privateKey", "secret", "password", "authorization":
			redacted.AddAttrs(slog.String(attribute.Key, "[REDACTED]"))
		default:
			redacted.AddAttrs(attribute)
		}
		return true
	})
	return handler.next.Handle(ctx, redacted)
}

func (handler *redactingHandler) WithAttrs(attributes []slog.Attr) slog.Handler {
	safe := make([]slog.Attr, 0, len(attributes))
	for _, attribute := range attributes {
		switch attribute.Key {
		case "token", "enrollmentToken", "privateKey", "secret", "password", "authorization":
			safe = append(safe, slog.String(attribute.Key, "[REDACTED]"))
		default:
			safe = append(safe, attribute)
		}
	}
	return &redactingHandler{next: handler.next.WithAttrs(safe)}
}

func (handler *redactingHandler) WithGroup(name string) slog.Handler {
	return &redactingHandler{next: handler.next.WithGroup(name)}
}

func Tail(path string, maximumLines int) ([]string, error) {
	if maximumLines <= 0 || maximumLines > 1000 {
		maximumLines = 100
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var rawLines []json.RawMessage
	for _, line := range splitLines(data) {
		if json.Valid(line) {
			rawLines = append(rawLines, append(json.RawMessage(nil), line...))
		}
	}
	if len(rawLines) > maximumLines {
		rawLines = rawLines[len(rawLines)-maximumLines:]
	}
	lines := make([]string, 0, len(rawLines))
	for _, line := range rawLines {
		lines = append(lines, string(line))
	}
	return lines, nil
}

func splitLines(data []byte) [][]byte {
	lines := make([][]byte, 0)
	start := 0
	for index, value := range data {
		if value == '\n' {
			if index > start {
				lines = append(lines, data[start:index])
			}
			start = index + 1
		}
	}
	if start < len(data) {
		lines = append(lines, data[start:])
	}
	return lines
}

func Timestamp() string {
	return time.Now().UTC().Format(time.RFC3339Nano)
}
