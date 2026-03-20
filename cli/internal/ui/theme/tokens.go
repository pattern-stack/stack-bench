package theme

// Category represents a semantic domain for color differentiation.
type Category int

const (
	CatAgent  Category = iota // Agent-related UI (accent, agent names)
	CatSystem                 // System chrome (borders, separators)
	CatTool                   // Tool calls, operations
	CatUser                   // User input, user-attributed content
	Cat5                      // Reserved
	Cat6                      // Reserved
	Cat7                      // Reserved
	Cat8                      // Reserved
)

// Hierarchy represents visual importance level.
type Hierarchy int

const (
	Primary   Hierarchy = iota // Titles, key information
	Secondary                  // Body text, normal content
	Tertiary                   // Supporting text, less important
	Quaternary                 // Least prominent, fine print
)

// Emphasis represents text weight/prominence.
type Emphasis int

const (
	Strong Emphasis = iota // Bold
	Normal                 // Default weight
	Subtle                 // Dim/faded
)

// Status represents an operational state.
type Status int

const (
	NoStatus Status = iota // No status applied
	Success
	Error
	Warning
	Info
	Muted
	Running
)

// Style composes all four token dimensions into a single styling intent.
type Style struct {
	Category  Category
	Hierarchy Hierarchy
	Emphasis  Emphasis
	Status    Status
}
