package identity

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

type Identity struct {
	PublicKey           string `json:"publicKey"`
	EncryptedPrivateKey string `json:"encryptedPrivateKey"`
}

type Material struct {
	PublicKey  ed25519.PublicKey
	PrivateKey ed25519.PrivateKey
}

func LoadOrCreate(dataDir string) (Material, error) {
	if err := os.MkdirAll(dataDir, 0o700); err != nil {
		return Material{}, err
	}
	identityPath := filepath.Join(dataDir, "identity.json")
	keyPath := filepath.Join(dataDir, "storage.key")
	if _, err := os.Stat(identityPath); err == nil {
		return load(identityPath, keyPath)
	} else if !errors.Is(err, os.ErrNotExist) {
		return Material{}, err
	}
	return create(identityPath, keyPath)
}

func create(identityPath, keyPath string) (Material, error) {
	storageKey := make([]byte, 32)
	if _, err := rand.Read(storageKey); err != nil {
		return Material{}, err
	}
	if err := writeProtected(keyPath, storageKey); err != nil {
		return Material{}, err
	}
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return Material{}, err
	}
	encrypted, err := encrypt(storageKey, privateKey)
	if err != nil {
		return Material{}, err
	}
	record := Identity{
		PublicKey:           base64.StdEncoding.EncodeToString(publicKey),
		EncryptedPrivateKey: base64.StdEncoding.EncodeToString(encrypted),
	}
	data, err := json.MarshalIndent(record, "", "  ")
	if err != nil {
		return Material{}, err
	}
	if err := writeProtected(identityPath, append(data, '\n')); err != nil {
		return Material{}, err
	}
	return Material{PublicKey: publicKey, PrivateKey: privateKey}, nil
}

func load(identityPath, keyPath string) (Material, error) {
	storageKey, err := os.ReadFile(keyPath)
	if err != nil {
		return Material{}, fmt.Errorf("load protected storage key: %w", err)
	}
	data, err := os.ReadFile(identityPath)
	if err != nil {
		return Material{}, err
	}
	var record Identity
	if err := json.Unmarshal(data, &record); err != nil {
		return Material{}, err
	}
	publicKey, err := base64.StdEncoding.DecodeString(record.PublicKey)
	if err != nil || len(publicKey) != ed25519.PublicKeySize {
		return Material{}, errors.New("invalid stored public key")
	}
	encrypted, err := base64.StdEncoding.DecodeString(record.EncryptedPrivateKey)
	if err != nil {
		return Material{}, errors.New("invalid stored private key encoding")
	}
	privateKey, err := decrypt(storageKey, encrypted)
	if err != nil || len(privateKey) != ed25519.PrivateKeySize {
		return Material{}, errors.New("cannot decrypt stored agent identity")
	}
	if !ed25519.PublicKey(publicKey).Equal(ed25519.PrivateKey(privateKey).Public()) {
		return Material{}, errors.New("stored agent identity key pair mismatch")
	}
	return Material{PublicKey: ed25519.PublicKey(publicKey), PrivateKey: ed25519.PrivateKey(privateKey)}, nil
}

func encrypt(key, plaintext []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	return append(nonce, gcm.Seal(nil, nonce, plaintext, nil)...), nil
}

func decrypt(key, ciphertext []byte) ([]byte, error) {
	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(ciphertext) < gcm.NonceSize() {
		return nil, errors.New("encrypted identity is truncated")
	}
	return gcm.Open(nil, ciphertext[:gcm.NonceSize()], ciphertext[gcm.NonceSize():], nil)
}

func writeProtected(path string, data []byte) error {
	temporary, err := os.CreateTemp(filepath.Dir(path), ".protected-*")
	if err != nil {
		return err
	}
	name := temporary.Name()
	defer os.Remove(name)
	if err := temporary.Chmod(0o600); err != nil && runtime.GOOS != "windows" {
		temporary.Close()
		return err
	}
	if _, err := temporary.Write(data); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Sync(); err != nil {
		temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	return os.Rename(name, path)
}

func PublicKeyBase64(material Material) string {
	return base64.StdEncoding.EncodeToString(material.PublicKey)
}

func Fingerprint(material Material) string {
	sum := sha256.Sum256(material.PublicKey)
	return hex.EncodeToString(sum[:])
}

func DeviceFingerprint() (string, error) {
	stableID, err := platformDeviceID()
	if err != nil {
		return "", err
	}
	hostname, err := os.Hostname()
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(runtime.GOOS + "\x00" + hostname + "\x00" + stableID))
	return hex.EncodeToString(sum[:]), nil
}
