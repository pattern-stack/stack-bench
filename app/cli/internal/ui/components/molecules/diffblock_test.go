package molecules

import (
	"strings"
	"testing"
)

const testDiff = `@@ -1,3 +1,4 @@
 package main
+import "fmt"
 func main() {
-    println("hello")
+    fmt.Println("hello")
 }`

func TestDiffBlock_ContainsFilePath(t *testing.T) {
	out := DiffBlock(darkCtx(), DiffBlockData{
		FilePath: "main.go",
		Hunks:    ParseUnifiedDiff(testDiff),
	})
	if !strings.Contains(out, "main.go") {
		t.Error("expected diff block to contain file path")
	}
}

func TestDiffBlock_ContainsAddedLine(t *testing.T) {
	out := DiffBlock(darkCtx(), DiffBlockData{
		FilePath: "main.go",
		Hunks:    ParseUnifiedDiff(testDiff),
	})
	if !strings.Contains(out, `import "fmt"`) {
		t.Error("expected diff block to contain added line content")
	}
}

func TestDiffBlock_ContainsRemovedLine(t *testing.T) {
	out := DiffBlock(darkCtx(), DiffBlockData{
		FilePath: "main.go",
		Hunks:    ParseUnifiedDiff(testDiff),
	})
	if !strings.Contains(out, `println("hello")`) {
		t.Error("expected diff block to contain removed line content")
	}
}

func TestDiffBlock_ContainsContextLine(t *testing.T) {
	out := DiffBlock(darkCtx(), DiffBlockData{
		FilePath: "main.go",
		Hunks:    ParseUnifiedDiff(testDiff),
	})
	if !strings.Contains(out, "package main") {
		t.Error("expected diff block to contain context line")
	}
}

func TestDiffBlock_ContainsHunkHeader(t *testing.T) {
	out := DiffBlock(darkCtx(), DiffBlockData{
		FilePath: "main.go",
		Hunks:    ParseUnifiedDiff(testDiff),
	})
	if !strings.Contains(out, "@@") {
		t.Error("expected diff block to contain hunk header")
	}
}

func TestDiffBlock_NoFilePath(t *testing.T) {
	out := DiffBlock(darkCtx(), DiffBlockData{
		Hunks: ParseUnifiedDiff("+added line"),
	})
	if !strings.Contains(out, "added line") {
		t.Error("expected diff block without file path to still render diff")
	}
}

func TestDiffBlock_AddedAndRemovedDiffer(t *testing.T) {
	added := DiffBlock(darkCtx(), DiffBlockData{Hunks: ParseUnifiedDiff("+new")})
	removed := DiffBlock(darkCtx(), DiffBlockData{Hunks: ParseUnifiedDiff("-old")})
	// They should render with different styling (colors)
	if added == removed {
		t.Error("expected added and removed lines to render differently")
	}
}

func TestDiffBlock_LightTheme(t *testing.T) {
	out := DiffBlock(lightCtx(), DiffBlockData{
		FilePath: "lib.go",
		Hunks:    ParseUnifiedDiff(testDiff),
	})
	if !strings.Contains(out, "lib.go") {
		t.Error("expected light theme diff block to contain file path")
	}
	if !strings.Contains(out, "package main") {
		t.Error("expected light theme diff block to contain diff content")
	}
}
