// Package molecules composes atoms into higher-level UI components.
// Molecules are pure functions: (RenderContext, Data) -> string.
// They never construct lipgloss styles directly — all styling goes through atoms.
package molecules
