package identity

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestIdentityIsPersistentAndPrivateKeyIsNotStoredInPlaintext(t *testing.T) {
	dataDir := t.TempDir()
	first, err := LoadOrCreate(dataDir)
	if err != nil {
		t.Fatal(err)
	}
	second, err := LoadOrCreate(dataDir)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(first.PublicKey, second.PublicKey) || !bytes.Equal(first.PrivateKey, second.PrivateKey) {
		t.Fatal("stored identity changed between loads")
	}
	stored, err := os.ReadFile(filepath.Join(dataDir, "identity.json"))
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(stored, first.PrivateKey) {
		t.Fatal("private key was stored in plaintext")
	}
	keyInfo, err := os.Stat(filepath.Join(dataDir, "storage.key"))
	if err != nil {
		t.Fatal(err)
	}
	if keyInfo.Mode().Perm()&0o077 != 0 {
		t.Fatalf("storage key permissions are too broad: %o", keyInfo.Mode().Perm())
	}
}
