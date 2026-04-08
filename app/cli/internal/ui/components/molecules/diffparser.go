package molecules

import (
	"strconv"
	"strings"
)

// DiffLineKind identifies whether a diff line was added, removed, or unchanged.
type DiffLineKind int

const (
	DiffLineContext DiffLineKind = iota
	DiffLineAdded
	DiffLineRemoved
)

// DiffLine is one line within a diff hunk. Content is the raw line without
// any leading +/- marker. OldNum and NewNum are 1-based line numbers within
// the old and new file respectively; they are zero when the line doesn't
// exist on that side (e.g., NewNum is 0 for a removed line).
type DiffLine struct {
	Kind    DiffLineKind
	Content string
	OldNum  int
	NewNum  int
}

// DiffHunk is a contiguous block of changes within a file. OldStart/NewStart
// are the 1-based starting line numbers from the unified diff hunk header.
// RawHeader preserves the original @@ line for display (may be empty if the
// hunk was built without a header, e.g., from a raw snippet).
type DiffHunk struct {
	OldStart, NewStart int
	RawHeader          string
	Lines              []DiffLine
}

// ParseUnifiedDiff parses a unified diff string into a slice of hunks. File
// headers (--- a/..., +++ b/...) before the first @@ hunk header are skipped.
// If the input has no @@ headers at all, a single synthetic hunk containing
// all lines is returned so ad-hoc diff snippets (e.g., "+new\n-old") render
// without forcing callers to construct a well-formed unified diff.
func ParseUnifiedDiff(diff string) []DiffHunk {
	if diff == "" {
		return nil
	}

	lines := strings.Split(diff, "\n")
	var hunks []DiffHunk
	var current *DiffHunk
	var oldLine, newLine int
	seenHunkHeader := false

	flush := func() {
		if current != nil {
			hunks = append(hunks, *current)
			current = nil
		}
	}

	for _, line := range lines {
		// File headers (--- a/..., +++ b/...) appear only before the first
		// @@ hunk header. Skip them in the pre-hunk region; once we're inside
		// a hunk, content lines that happen to start with -- or ++ are real
		// content (extremely rare in practice but we handle it correctly).
		if !seenHunkHeader {
			if strings.HasPrefix(line, "--- ") || strings.HasPrefix(line, "+++ ") {
				continue
			}
		}

		switch {
		case strings.HasPrefix(line, "@@"):
			flush()
			oldStart, newStart := parseHunkHeader(line)
			current = &DiffHunk{
				OldStart:  oldStart,
				NewStart:  newStart,
				RawHeader: line,
			}
			oldLine, newLine = oldStart, newStart
			seenHunkHeader = true
		case strings.HasPrefix(line, "+"):
			if current == nil {
				current = &DiffHunk{}
			}
			current.Lines = append(current.Lines, DiffLine{
				Kind:    DiffLineAdded,
				Content: strings.TrimPrefix(line, "+"),
				NewNum:  newLine,
			})
			newLine++
		case strings.HasPrefix(line, "-"):
			if current == nil {
				current = &DiffHunk{}
			}
			current.Lines = append(current.Lines, DiffLine{
				Kind:    DiffLineRemoved,
				Content: strings.TrimPrefix(line, "-"),
				OldNum:  oldLine,
			})
			oldLine++
		default:
			if current == nil {
				current = &DiffHunk{}
			}
			// Context lines in unified diff format start with a space; trim
			// exactly one leading space if present, otherwise use the line
			// as-is (tolerates inputs without the leading space).
			content := line
			if strings.HasPrefix(content, " ") {
				content = content[1:]
			}
			current.Lines = append(current.Lines, DiffLine{
				Kind:    DiffLineContext,
				Content: content,
				OldNum:  oldLine,
				NewNum:  newLine,
			})
			oldLine++
			newLine++
		}
	}
	flush()
	return hunks
}

// parseHunkHeader extracts old and new start line numbers from a unified
// diff hunk header of the form "@@ -old,count +new,count @@ [context]".
// Missing or malformed counts default to zero.
func parseHunkHeader(line string) (oldStart, newStart int) {
	parts := strings.SplitN(line, " ", 4)
	if len(parts) >= 3 {
		if old := strings.TrimPrefix(parts[1], "-"); old != "" {
			if n, _, ok := strings.Cut(old, ","); ok {
				oldStart, _ = strconv.Atoi(n)
			} else {
				oldStart, _ = strconv.Atoi(old)
			}
		}
		if nw := strings.TrimPrefix(parts[2], "+"); nw != "" {
			if n, _, ok := strings.Cut(nw, ","); ok {
				newStart, _ = strconv.Atoi(n)
			} else {
				newStart, _ = strconv.Atoi(nw)
			}
		}
	}
	return
}
