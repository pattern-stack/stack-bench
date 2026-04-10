package molecules

import "testing"

func TestParseUnifiedDiff_EmptyInput(t *testing.T) {
	if h := ParseUnifiedDiff(""); h != nil {
		t.Errorf("expected nil hunks for empty input, got %v", h)
	}
}

func TestParseUnifiedDiff_SkipsFileHeaders(t *testing.T) {
	diff := `--- a/main.go
+++ b/main.go
@@ -1,2 +1,2 @@
-old
+new`
	hunks := ParseUnifiedDiff(diff)
	if len(hunks) != 1 {
		t.Fatalf("expected 1 hunk, got %d", len(hunks))
	}
	if len(hunks[0].Lines) != 2 {
		t.Fatalf("expected 2 lines, got %d", len(hunks[0].Lines))
	}
	if hunks[0].Lines[0].Content != "old" || hunks[0].Lines[0].Kind != DiffLineRemoved {
		t.Errorf("line 0: got %+v", hunks[0].Lines[0])
	}
	if hunks[0].Lines[1].Content != "new" || hunks[0].Lines[1].Kind != DiffLineAdded {
		t.Errorf("line 1: got %+v", hunks[0].Lines[1])
	}
}

func TestParseUnifiedDiff_LineNumbersFromHunkHeader(t *testing.T) {
	diff := `@@ -10,3 +20,4 @@
 context
-removed
+added1
+added2`
	hunks := ParseUnifiedDiff(diff)
	if len(hunks) != 1 {
		t.Fatalf("expected 1 hunk, got %d", len(hunks))
	}
	h := hunks[0]
	if h.OldStart != 10 || h.NewStart != 20 {
		t.Errorf("expected start (10, 20), got (%d, %d)", h.OldStart, h.NewStart)
	}
	// context: old=10, new=20
	if h.Lines[0].OldNum != 10 || h.Lines[0].NewNum != 20 {
		t.Errorf("context line: got old=%d new=%d", h.Lines[0].OldNum, h.Lines[0].NewNum)
	}
	// removed: old=11
	if h.Lines[1].OldNum != 11 {
		t.Errorf("removed line: got old=%d", h.Lines[1].OldNum)
	}
	// added1: new=21
	if h.Lines[2].NewNum != 21 {
		t.Errorf("added1: got new=%d", h.Lines[2].NewNum)
	}
	// added2: new=22
	if h.Lines[3].NewNum != 22 {
		t.Errorf("added2: got new=%d", h.Lines[3].NewNum)
	}
}

func TestParseUnifiedDiff_MultipleHunks(t *testing.T) {
	diff := `@@ -1,2 +1,2 @@
-a
+A
@@ -10,2 +10,2 @@
-b
+B`
	hunks := ParseUnifiedDiff(diff)
	if len(hunks) != 2 {
		t.Fatalf("expected 2 hunks, got %d", len(hunks))
	}
	if hunks[0].OldStart != 1 || hunks[1].OldStart != 10 {
		t.Errorf("hunk starts: got %d and %d", hunks[0].OldStart, hunks[1].OldStart)
	}
}

func TestParseUnifiedDiff_BareSnippetWithoutHeader(t *testing.T) {
	// Ad-hoc snippets without any @@ header still parse into a single hunk
	// so callers can pass raw diff fragments.
	hunks := ParseUnifiedDiff("+new line")
	if len(hunks) != 1 {
		t.Fatalf("expected 1 synthetic hunk, got %d", len(hunks))
	}
	if hunks[0].RawHeader != "" {
		t.Errorf("synthetic hunk should have empty RawHeader, got %q", hunks[0].RawHeader)
	}
	if len(hunks[0].Lines) != 1 || hunks[0].Lines[0].Kind != DiffLineAdded {
		t.Errorf("expected 1 added line, got %+v", hunks[0].Lines)
	}
}

func TestParseUnifiedDiff_ContextLineTrimsLeadingSpace(t *testing.T) {
	diff := `@@ -1,1 +1,1 @@
 package main`
	hunks := ParseUnifiedDiff(diff)
	if got := hunks[0].Lines[0].Content; got != "package main" {
		t.Errorf("expected leading space trimmed, got %q", got)
	}
}

func TestParseHunkHeader_BasicForm(t *testing.T) {
	old, nw := parseHunkHeader("@@ -8,5 +8,8 @@")
	if old != 8 || nw != 8 {
		t.Errorf("got (%d, %d)", old, nw)
	}
}

func TestParseHunkHeader_NoCount(t *testing.T) {
	old, nw := parseHunkHeader("@@ -8 +20 @@")
	if old != 8 || nw != 20 {
		t.Errorf("got (%d, %d)", old, nw)
	}
}

func TestParseHunkHeader_WithFunctionContext(t *testing.T) {
	old, nw := parseHunkHeader("@@ -8,5 +8,8 @@ func main() {")
	if old != 8 || nw != 8 {
		t.Errorf("got (%d, %d)", old, nw)
	}
}
