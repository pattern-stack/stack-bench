// Package themes embeds the YAML theme files.
package themes

import _ "embed"

//go:embed dark.yml
var DarkYAML []byte

//go:embed light.yml
var LightYAML []byte
