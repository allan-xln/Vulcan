package main

import (
	"crypto/rand"
	"debug/buildinfo"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"
)

type component struct {
	Type       string     `json:"type"`
	Name       string     `json:"name"`
	Version    string     `json:"version,omitempty"`
	PURL       string     `json:"purl,omitempty"`
	Properties []property `json:"properties,omitempty"`
}

type property struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type bom struct {
	BOMFormat    string      `json:"bomFormat"`
	SpecVersion  string      `json:"specVersion"`
	SerialNumber string      `json:"serialNumber"`
	Version      int         `json:"version"`
	Metadata     metadata    `json:"metadata"`
	Components   []component `json:"components"`
}

type metadata struct {
	Timestamp string    `json:"timestamp"`
	Component component `json:"component"`
}

func main() {
	binaryPath := flag.String("binary", "", "compiled Vulcan Agent binary")
	outputPath := flag.String("output", "", "CycloneDX JSON output")
	releaseVersion := flag.String("version", "", "Vulcan Agent release version")
	flag.Parse()
	if *binaryPath == "" || *outputPath == "" {
		fatal(errors.New("--binary and --output are required"))
	}
	info, err := buildinfo.ReadFile(*binaryPath)
	if err != nil {
		fatal(err)
	}
	components := make([]component, 0, len(info.Deps))
	for _, dependency := range info.Deps {
		version := dependency.Version
		path := dependency.Path
		if dependency.Replace != nil {
			path = dependency.Replace.Path
			version = dependency.Replace.Version
		}
		components = append(components, component{
			Type:    "library",
			Name:    path,
			Version: version,
			PURL:    goPURL(path, version),
			Properties: []property{
				{Name: "vulcan:build:goVersion", Value: info.GoVersion},
			},
		})
	}
	mainVersion := *releaseVersion
	if mainVersion == "" {
		mainVersion = info.Main.Version
	}
	serialNumber, err := newSerialNumber()
	if err != nil {
		fatal(err)
	}
	document := bom{
		BOMFormat:    "CycloneDX",
		SpecVersion:  "1.5",
		SerialNumber: serialNumber,
		Version:      1,
		Metadata: metadata{
			Timestamp: time.Now().UTC().Format(time.RFC3339),
			Component: component{
				Type:    "application",
				Name:    "vulcan-agent",
				Version: mainVersion,
			},
		},
		Components: components,
	}
	data, err := json.MarshalIndent(document, "", "  ")
	if err != nil {
		fatal(err)
	}
	if err := os.WriteFile(*outputPath, append(data, '\n'), 0o644); err != nil {
		fatal(err)
	}
}

func newSerialNumber() (string, error) {
	value := make([]byte, 16)
	if _, err := rand.Read(value); err != nil {
		return "", err
	}
	value[6] = (value[6] & 0x0f) | 0x40
	value[8] = (value[8] & 0x3f) | 0x80
	encoded := hex.EncodeToString(value)
	return fmt.Sprintf(
		"urn:uuid:%s-%s-%s-%s-%s",
		encoded[0:8],
		encoded[8:12],
		encoded[12:16],
		encoded[16:20],
		encoded[20:32],
	), nil
}

func goPURL(path, version string) string {
	if version == "" || version == "(devel)" {
		return "pkg:golang/" + path
	}
	return "pkg:golang/" + path + "@" + strings.TrimPrefix(version, "v")
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, err)
	os.Exit(1)
}
