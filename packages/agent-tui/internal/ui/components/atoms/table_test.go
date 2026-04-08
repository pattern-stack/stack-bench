package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

func stripANSITest(s string) string {
	var out strings.Builder
	i := 0
	for i < len(s) {
		if s[i] == '\x1b' && i+1 < len(s) && s[i+1] == '[' {
			j := i + 2
			for j < len(s) && s[j] != 'm' {
				j++
			}
			if j < len(s) {
				i = j + 1
				continue
			}
		}
		out.WriteByte(s[i])
		i++
	}
	return out.String()
}

func TestTableBasic(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := TableData{
		Headers: []string{"Name", "Age"},
		Rows: [][]string{
			{"Alice", "30"},
			{"Bob", "25"},
		},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table returned empty string for valid data")
	}
	plain := stripANSITest(result)
	if !strings.Contains(plain, "Name") {
		t.Errorf("expected header 'Name' in output, got: %s", plain)
	}
	if !strings.Contains(plain, "Alice") {
		t.Errorf("expected cell 'Alice' in output, got: %s", plain)
	}
}

func TestTableEmpty(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := TableData{}

	result := Table(ctx, data)
	if result != "" {
		t.Errorf("expected empty string for empty table, got: %q", result)
	}
}

func TestTableSingleColumn(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := TableData{
		Headers: []string{"Item"},
		Rows: [][]string{
			{"Apple"},
			{"Banana"},
		},
	}

	result := Table(ctx, data)
	plain := stripANSITest(result)
	if !strings.Contains(plain, "Apple") {
		t.Errorf("expected cell 'Apple' in output, got: %s", plain)
	}
}

func TestTableMixedAlignments(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := TableData{
		Headers:    []string{"Left", "Center", "Right"},
		Rows:       [][]string{{"a", "b", "c"}},
		Alignments: []TableAlignment{AlignLeft, AlignCenter, AlignRight},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table returned empty string")
	}
	plain := stripANSITest(result)
	for _, expected := range []string{"Left", "Center", "Right", "a", "b", "c"} {
		if !strings.Contains(plain, expected) {
			t.Errorf("expected %q in output, got: %s", expected, plain)
		}
	}
}

func TestTableWidthConstraint(t *testing.T) {
	data := TableData{
		Headers: []string{"Name", "Description"},
		Rows:    [][]string{{"Short", "A brief item"}},
	}

	narrow := Table(testContext(theme.DarkTheme(), 40), data)
	wide := Table(testContext(theme.DarkTheme(), 120), data)

	narrowLines := strings.Split(stripANSITest(narrow), "\n")
	wideLines := strings.Split(stripANSITest(wide), "\n")

	narrowWidth := len([]rune(narrowLines[0]))
	wideWidth := len([]rune(wideLines[0]))

	if narrowWidth >= wideWidth {
		t.Errorf("narrow table (%d runes) should be narrower than wide table (%d runes)", narrowWidth, wideWidth)
	}
}

func TestTableDarkVsLight(t *testing.T) {
	data := TableData{
		Headers: []string{"Key", "Value"},
		Rows:    [][]string{{"x", "1"}},
	}
	dark := Table(testContext(theme.DarkTheme(), 60), data)
	light := Table(testContext(theme.LightTheme(), 60), data)

	if dark == light {
		t.Error("expected different output for dark vs light themes")
	}
}

func TestTableHasRoundedBorder(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Headers: []string{"X"},
		Rows:    [][]string{{"1"}},
	}

	result := Table(ctx, data)
	plain := stripANSITest(result)
	if !strings.Contains(plain, "\u256d") {
		t.Errorf("expected rounded top-left corner in output, got: %s", plain)
	}
}
