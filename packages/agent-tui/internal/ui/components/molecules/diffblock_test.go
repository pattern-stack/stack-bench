package molecules

import (
	"strings"
	"testing"

	"github.com/dugshub/agent-tui/internal/ui/theme"
)

func TestDiffBlockRendersFilename(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := DiffBlock(ctx, DiffBlockData{
		Filename: "main.go",
		Lines: []DiffLine{
			{Type: DiffContext, Content: "package main"},
		},
	})
	if !strings.Contains(result, "main.go") {
		t.Error("should contain filename")
	}
}

func TestDiffBlockAddedLines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := DiffBlock(ctx, DiffBlockData{
		Filename: "main.go",
		Lines: []DiffLine{
			{Type: DiffAdded, Content: "fmt.Println(\"hello\")"},
		},
	})
	if !strings.Contains(result, "fmt.Println") {
		t.Error("should contain added line content")
	}
}

func TestDiffBlockRemovedLines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := DiffBlock(ctx, DiffBlockData{
		Filename: "main.go",
		Lines: []DiffLine{
			{Type: DiffRemoved, Content: "old code here"},
		},
	})
	if !strings.Contains(result, "old code here") {
		t.Error("should contain removed line content")
	}
}

func TestDiffBlockContextLines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := DiffBlock(ctx, DiffBlockData{
		Filename: "main.go",
		Lines: []DiffLine{
			{Type: DiffContext, Content: "unchanged line"},
		},
	})
	if !strings.Contains(result, "unchanged line") {
		t.Error("should contain context line content")
	}
}

func TestDiffBlockMixedLines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	result := DiffBlock(ctx, DiffBlockData{
		Filename: "main.go",
		Lines: []DiffLine{
			{Type: DiffContext, Content: "context"},
			{Type: DiffRemoved, Content: "removed"},
			{Type: DiffAdded, Content: "added"},
		},
	})
	for _, want := range []string{"context", "removed", "added"} {
		if !strings.Contains(result, want) {
			t.Errorf("should contain %q", want)
		}
	}
}

func TestDiffBlockParseUnifiedDiff(t *testing.T) {
	diff := `--- a/main.go
+++ b/main.go
@@ -1,3 +1,3 @@
 package main
-old line
+new line
 end`
	lines := ParseUnifiedDiff(diff)

	// Should skip --- and +++ headers and @@ hunk headers
	if len(lines) != 4 {
		t.Fatalf("expected 4 lines, got %d", len(lines))
	}

	if lines[0].Type != DiffContext || lines[0].Content != "package main" {
		t.Errorf("line 0: expected context 'package main', got %v %q", lines[0].Type, lines[0].Content)
	}
	if lines[1].Type != DiffRemoved || lines[1].Content != "old line" {
		t.Errorf("line 1: expected removed 'old line', got %v %q", lines[1].Type, lines[1].Content)
	}
	if lines[2].Type != DiffAdded || lines[2].Content != "new line" {
		t.Errorf("line 2: expected added 'new line', got %v %q", lines[2].Type, lines[2].Content)
	}
	if lines[3].Type != DiffContext || lines[3].Content != "end" {
		t.Errorf("line 3: expected context 'end', got %v %q", lines[3].Type, lines[3].Content)
	}
}

func TestDiffBlockDifferentThemes(t *testing.T) {
	data := DiffBlockData{
		Filename: "main.go",
		Lines: []DiffLine{
			{Type: DiffAdded, Content: "new"},
			{Type: DiffRemoved, Content: "old"},
		},
	}
	dark := DiffBlock(testContext(theme.DarkTheme(), 80), data)
	light := DiffBlock(testContext(theme.LightTheme(), 80), data)
	if dark == light {
		t.Error("dark and light themes should produce different output")
	}
}

func TestDiffBlockEmptyLines(t *testing.T) {
	ctx := testContext(theme.DarkTheme(), 80)
	// Should not panic on empty input
	result := DiffBlock(ctx, DiffBlockData{
		Filename: "empty.go",
		Lines:    nil,
	})
	if !strings.Contains(result, "empty.go") {
		t.Error("should still render filename header")
	}

	// Also test ParseUnifiedDiff with empty string
	lines := ParseUnifiedDiff("")
	if len(lines) != 0 {
		t.Errorf("expected 0 lines from empty diff, got %d", len(lines))
	}
}
