package atoms

import (
	"strings"
	"testing"

	"github.com/dugshub/agentic-tui/internal/ui/theme"
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
	if !strings.Contains(plain, "Age") {
		t.Errorf("expected header 'Age' in output, got: %s", plain)
	}
	if !strings.Contains(plain, "Alice") {
		t.Errorf("expected cell 'Alice' in output, got: %s", plain)
	}
	if !strings.Contains(plain, "Bob") {
		t.Errorf("expected cell 'Bob' in output, got: %s", plain)
	}
	if !strings.Contains(plain, "30") {
		t.Errorf("expected cell '30' in output, got: %s", plain)
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

func TestTableEmptyHeaders(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	data := TableData{
		Headers: []string{},
		Rows:    [][]string{},
	}

	result := Table(ctx, data)
	if result != "" {
		t.Errorf("expected empty string for empty headers and rows, got: %q", result)
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
	if !strings.Contains(plain, "Item") {
		t.Errorf("expected header 'Item' in output, got: %s", plain)
	}
	if !strings.Contains(plain, "Apple") {
		t.Errorf("expected cell 'Apple' in output, got: %s", plain)
	}
	if !strings.Contains(plain, "Banana") {
		t.Errorf("expected cell 'Banana' in output, got: %s", plain)
	}
}

func TestTableAlignmentLeft(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Headers:    []string{"Left"},
		Rows:       [][]string{{"data"}},
		Alignments: []TableAlignment{AlignLeft},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table returned empty string")
	}
	plain := stripANSITest(result)
	if !strings.Contains(plain, "data") {
		t.Errorf("expected 'data' in output, got: %s", plain)
	}
}

func TestTableAlignmentCenter(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Headers:    []string{"Center"},
		Rows:       [][]string{{"data"}},
		Alignments: []TableAlignment{AlignCenter},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table returned empty string")
	}
	plain := stripANSITest(result)
	if !strings.Contains(plain, "data") {
		t.Errorf("expected 'data' in output, got: %s", plain)
	}
}

func TestTableAlignmentRight(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Headers:    []string{"Right"},
		Rows:       [][]string{{"data"}},
		Alignments: []TableAlignment{AlignRight},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table returned empty string")
	}
	plain := stripANSITest(result)
	if !strings.Contains(plain, "data") {
		t.Errorf("expected 'data' in output, got: %s", plain)
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
	// A wide table rendered at width=40 should be narrower than one at width=120.
	data := TableData{
		Headers: []string{"Name", "Description"},
		Rows: [][]string{
			{"Short", "A brief item"},
		},
	}

	narrow := Table(testContext(theme.DarkTheme(), 40), data)
	wide := Table(testContext(theme.DarkTheme(), 120), data)

	if narrow == "" {
		t.Fatal("Table returned empty string at width 40")
	}
	if wide == "" {
		t.Fatal("Table returned empty string at width 120")
	}

	// The narrow table should have shorter lines than the wide one.
	narrowLines := strings.Split(stripANSITest(narrow), "\n")
	wideLines := strings.Split(stripANSITest(wide), "\n")

	if len(narrowLines) == 0 || len(wideLines) == 0 {
		t.Fatal("expected at least one line in both tables")
	}

	// Compare the first line (top border) lengths using rune count for visual width.
	narrowWidth := len([]rune(narrowLines[0]))
	wideWidth := len([]rune(wideLines[0]))

	if narrowWidth >= wideWidth {
		t.Errorf("narrow table (%d runes) should be narrower than wide table (%d runes)", narrowWidth, wideWidth)
	}
}

func TestTableNarrowWidth(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 20)
	data := TableData{
		Headers: []string{"Col1", "Col2"},
		Rows:    [][]string{{"val1", "val2"}},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table returned empty string for narrow width")
	}
}

func TestTableDarkTheme(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Headers: []string{"A"},
		Rows:    [][]string{{"1"}},
	}
	dark := Table(ctx, data)
	if dark == "" {
		t.Fatal("dark theme table returned empty string")
	}
}

func TestTableLightTheme(t *testing.T) {
	ctx := testContext(theme.LightTheme(), 60)
	data := TableData{
		Headers: []string{"A"},
		Rows:    [][]string{{"1"}},
	}
	light := Table(ctx, data)
	if light == "" {
		t.Fatal("light theme table returned empty string")
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

func TestTableHeadersOnly(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Headers: []string{"Col1", "Col2"},
	}

	result := Table(ctx, data)
	// Headers-only should still render.
	if result == "" {
		t.Fatal("Table with only headers returned empty string")
	}
	plain := stripANSITest(result)
	if !strings.Contains(plain, "Col1") {
		t.Errorf("expected 'Col1' in output, got: %s", plain)
	}
}

func TestTableRowsOnly(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 60)
	data := TableData{
		Rows: [][]string{
			{"a", "b"},
			{"c", "d"},
		},
	}

	result := Table(ctx, data)
	if result == "" {
		t.Fatal("Table with only rows returned empty string")
	}
	plain := stripANSITest(result)
	if !strings.Contains(plain, "a") {
		t.Errorf("expected 'a' in output, got: %s", plain)
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
	// Rounded border uses curved corners.
	if !strings.Contains(plain, "\u256d") {
		t.Errorf("expected rounded top-left corner in output, got: %s", plain)
	}
	if !strings.Contains(plain, "\u256e") {
		t.Errorf("expected rounded top-right corner in output, got: %s", plain)
	}
	if !strings.Contains(plain, "\u2570") {
		t.Errorf("expected rounded bottom-left corner in output, got: %s", plain)
	}
	if !strings.Contains(plain, "\u256f") {
		t.Errorf("expected rounded bottom-right corner in output, got: %s", plain)
	}
}
