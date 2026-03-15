package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/muesli/termenv"
)

// ═══════════════════════════════════════════════════════════════════
// Colors
// ═══════════════════════════════════════════════════════════════════

var (
	colorAccent = lipgloss.AdaptiveColor{Light: "#7D56F4", Dark: "#BD93F9"}
	colorGreen  = lipgloss.AdaptiveColor{Light: "#2E7D32", Dark: "#50FA7B"}
	colorRed    = lipgloss.AdaptiveColor{Light: "#C62828", Dark: "#FF5555"}
	colorDim    = lipgloss.AdaptiveColor{Light: "#999999", Dark: "#6272A4"}
	colorFg     = lipgloss.AdaptiveColor{Light: "#282A36", Dark: "#F8F8F2"}
	colorMag    = lipgloss.AdaptiveColor{Light: "#6A1B9A", Dark: "#FF79C6"}
)

var (
	dimS    = lipgloss.NewStyle().Foreground(colorDim)
	fgS     = lipgloss.NewStyle().Foreground(colorFg)
	boldS   = lipgloss.NewStyle().Bold(true).Foreground(colorFg)
	greenS  = lipgloss.NewStyle().Foreground(colorGreen)
	redS    = lipgloss.NewStyle().Foreground(colorRed)
	accentS = lipgloss.NewStyle().Foreground(colorAccent)
	magS    = lipgloss.NewStyle().Foreground(colorMag)
)

// ═══════════════════════════════════════════════════════════════════
// Tabs
// ═══════════════════════════════════════════════════════════════════

type tabID int

const (
	tabStacks tabID = iota
	tabStreams
	tabChat
	tabCount
)

var tabNames = [tabCount]string{"Stacks", "Streams", "Chat"}

// ═══════════════════════════════════════════════════════════════════
// Stack types
// ═══════════════════════════════════════════════════════════════════

type bState int

const (
	bsMerged bState = iota
	bsActive
	bsBlocked
	bsQueued
)

type commit struct{ hash, msg, age string }

type branch struct {
	name      string
	state     bState
	commits   []commit
	origCount int
	day       int
	pr        int
	submitted bool
	published bool
	blockOn   string
}

type stack struct {
	name     string
	color    lipgloss.AdaptiveColor
	branches []branch
	deps     []string
	archived bool
	doneDay  int
}

type proj struct {
	name           string
	day, totalDays int
	stacks         []stack
}

type navItem struct{ si, bi int }

// ═══════════════════════════════════════════════════════════════════
// Stream types — 3-level drill-down
// ═══════════════════════════════════════════════════════════════════

type phStatus int

const (
	phDone phStatus = iota
	phActive
	phWaiting
)

type agStatus int

const (
	agDone agStatus = iota
	agActive
	agWaiting
)

type toolKind int

const (
	tkRead toolKind = iota
	tkEdit
	tkBash
	tkGrep
)

func (t toolKind) String() string {
	return [...]string{"Read", "Edit", "Bash", "Grep"}[t]
}

type toolCall struct {
	kind     toolKind
	target   string
	result   string
	duration string
	diffLines []string // for Edit calls: +/- prefixed lines
}

type agentMsg struct {
	role    string // "thought" or "response"
	content string
	tools   []toolCall
}

type fileDiff struct {
	path    string
	added   int
	removed int
	hunks   []string
}

type taskAgent struct {
	name, model, tokens, duration, summary string
	status                                 agStatus
	messages                               []agentMsg
	files                                  []fileDiff
}

type taskPhase struct {
	name   string
	status phStatus
}

type taskSession struct {
	id, title, branch, tokens, elapsed string
	loopName                           string // "/plan_w_team" or "/develop"
	phases                             []taskPhase
	agents                             []taskAgent
}

type streamLevel int

const (
	lvOverview streamLevel = iota
	lvTask
	lvAgent
)

// ═══════════════════════════════════════════════════════════════════
// Model
// ═══════════════════════════════════════════════════════════════════

type model struct {
	width, height int
	tab           tabID

	// Stacks
	project  proj
	cursor   int
	expanded int

	// Streams
	tasks         []taskSession
	streamLvl     streamLevel
	taskCur       int
	agentCur      int
	agentPane     int // 0=messages, 1=files
	msgScroll     int
	fileCursor    int
	toolsExpanded bool

	// Chat
	chatMsgs []string
}

func (m model) navItems() []navItem {
	var items []navItem
	for si, s := range m.project.stacks {
		if s.archived {
			continue
		}
		for bi := range s.branches {
			items = append(items, navItem{si, bi})
		}
	}
	return items
}

func initialModel() model {
	return model{
		width: 120, height: 40,
		project:       fakeProject(),
		cursor:        2,
		expanded:      2,
		tasks:         fakeTasks(),
		streamLvl:     lvOverview,
		toolsExpanded: true,
		chatMsgs: []string{
			"Working on session API — 4 commits so far.",
			"Next: wire refresh endpoint, then submit for review.",
			"jwt-middleware/2 is blocked waiting on this.",
		},
	}
}

// ═══════════════════════════════════════════════════════════════════
// Bubble Tea
// ═══════════════════════════════════════════════════════════════════

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil
	case tea.KeyMsg:
		k := msg.String()
		switch k {
		case "ctrl+c":
			return m, tea.Quit
		case "q":
			if m.tab != tabChat {
				return m, tea.Quit
			}
		case "tab":
			if m.tab == tabStreams && m.streamLvl == lvAgent {
				m.agentPane = 1 - m.agentPane
				return m, nil
			}
			m.tab = (m.tab + 1) % tabCount
			return m, nil
		case "shift+tab":
			m.tab = (m.tab + tabCount - 1) % tabCount
			return m, nil
		}
		switch m.tab {
		case tabStacks:
			m = m.updateStacks(k)
		case tabStreams:
			m = m.updateStreams(k)
		}
	}
	return m, nil
}

func (m model) View() string {
	if m.width < 50 {
		return "resize terminal (min 50 cols)"
	}
	tabs := m.renderTabs()
	status := m.renderStatus()
	ch := m.height - lipgloss.Height(tabs) - lipgloss.Height(status)
	if ch < 1 {
		ch = 1
	}
	var body string
	switch m.tab {
	case tabStacks:
		body = m.viewStacks(ch)
	case tabStreams:
		body = m.viewStreams(ch)
	case tabChat:
		body = m.viewChat(ch)
	}
	return tabs + "\n" + body + "\n" + status
}

func (m model) renderTabs() string {
	var parts []string
	for i := tabID(0); i < tabCount; i++ {
		if i == m.tab {
			s := lipgloss.NewStyle().Bold(true).Foreground(colorAccent).
				BorderBottom(true).BorderStyle(lipgloss.ThickBorder()).BorderBottomForeground(colorAccent)
			parts = append(parts, s.Render(" "+tabNames[i]+" "))
		} else {
			parts = append(parts, dimS.Render(" "+tabNames[i]+" "))
		}
	}
	row := lipgloss.JoinHorizontal(lipgloss.Bottom, parts...)
	fill := dimS.Render(strings.Repeat("─", maxI(0, m.width-lipgloss.Width(row))))
	return row + fill
}

func (m model) renderStatus() string {
	var hint string
	switch m.tab {
	case tabStacks:
		hint = "j/k:navigate  enter:expand  s:submit  p:publish  1-3:jump stack  q:quit"
	case tabStreams:
		switch m.streamLvl {
		case lvOverview:
			hint = "j/k:navigate  enter:drill-in  q:quit"
		case lvTask:
			hint = "j/k:navigate  enter:drill-in  esc:back  q:quit"
		case lvAgent:
			hint = "j/k:scroll  tab:switch pane  enter:toggle tools  esc:back  q:quit"
		}
	case tabChat:
		hint = "tab:switch view"
	}
	return dimS.Render(strings.Repeat("─", m.width)) + "\n" + dimS.Render(" "+hint)
}

// ═══════════════════════════════════════════════════════════════════
// STACKS VIEW (unchanged)
// ═══════════════════════════════════════════════════════════════════

func (m model) updateStacks(k string) model {
	items := m.navItems()
	if len(items) == 0 {
		return m
	}
	switch k {
	case "j", "down":
		if m.cursor < len(items)-1 {
			m.cursor++
		}
	case "k", "up":
		if m.cursor > 0 {
			m.cursor--
		}
	case "enter":
		if m.expanded == m.cursor {
			m.expanded = -1
		} else {
			m.expanded = m.cursor
		}
	case "esc":
		m.expanded = -1
	case "s":
		ni := items[m.cursor]
		b := &m.project.stacks[ni.si].branches[ni.bi]
		if b.state == bsActive && !b.submitted {
			b.submitted = true
		}
	case "p":
		ni := items[m.cursor]
		b := &m.project.stacks[ni.si].branches[ni.bi]
		if b.state == bsActive && b.submitted && !b.published {
			b.published = true
			b.pr = 15
		}
	case "1", "2", "3":
		idx, _ := strconv.Atoi(k)
		idx--
		aidx := 0
		for si, s := range m.project.stacks {
			if s.archived {
				continue
			}
			if aidx == idx {
				for i, it := range items {
					if it.si == si {
						m.cursor = i
						return m
					}
				}
			}
			aidx++
		}
	}
	return m
}

func (m model) viewStacks(h int) string {
	p := m.project
	items := m.navItems()
	var lines []string

	var dots []string
	for i := 1; i <= p.totalDays; i++ {
		if i <= p.day {
			dots = append(dots, accentS.Render("●"))
		} else {
			dots = append(dots, dimS.Render("○"))
		}
	}
	titleL := " " + boldS.Render(strings.ToUpper(p.name))
	dayR := dimS.Render(fmt.Sprintf("Day %d/%d", p.day, p.totalDays)) + "  " + strings.Join(dots, " ")
	lines = append(lines, padR(titleL, m.width-lipgloss.Width(dayR))+dayR)

	var mc, ac, bc, qc, activeStacks, totalBranches int
	for _, s := range p.stacks {
		if s.archived {
			continue
		}
		activeStacks++
		totalBranches += len(s.branches)
		for _, b := range s.branches {
			switch b.state {
			case bsMerged:
				mc++
			case bsActive:
				ac++
			case bsBlocked:
				bc++
			case bsQueued:
				qc++
			}
		}
	}
	sL := dimS.Render(fmt.Sprintf(" %d stacks · %d branches", activeStacks, totalBranches))
	var sp []string
	if mc > 0 {
		sp = append(sp, greenS.Render(fmt.Sprintf("%d merged", mc)))
	}
	if ac > 0 {
		sp = append(sp, accentS.Render(fmt.Sprintf("%d active", ac)))
	}
	if bc > 0 {
		sp = append(sp, redS.Render(fmt.Sprintf("%d blocked", bc)))
	}
	if qc > 0 {
		sp = append(sp, dimS.Render(fmt.Sprintf("%d queued", qc)))
	}
	sR := strings.Join(sp, "  ")
	lines = append(lines, padR(sL, m.width-lipgloss.Width(sR))+sR)

	for si, s := range p.stacks {
		_ = si
		lines = append(lines, "")
		sty := lipgloss.NewStyle().Foreground(s.color)

		if s.archived {
			hL := " " + greenS.Render("✓") + " " + dimS.Render(s.name)
			hR := dimS.Render(fmt.Sprintf("completed day %d · archived", s.doneDay))
			lines = append(lines, padR(hL, m.width-lipgloss.Width(hR))+hR)
			lines = append(lines, dimS.Render(fmt.Sprintf("   %d/%d branches merged", len(s.branches), len(s.branches))))
			continue
		}

		mergedC := 0
		for _, b := range s.branches {
			if b.state == bsMerged {
				mergedC++
			}
		}
		hL := " " + sty.Render("─ "+s.name+" ")
		hR := sty.Render(fmt.Sprintf(" %d/%d merged ─", mergedC, len(s.branches)))
		fw := m.width - lipgloss.Width(hL) - lipgloss.Width(hR)
		if fw < 0 {
			fw = 0
		}
		lines = append(lines, hL+sty.Render(strings.Repeat("─", fw))+hR)

		if len(s.deps) > 0 {
			lines = append(lines, "   "+dimS.Render("needs: "+strings.Join(s.deps, " + ")))
		}

		for bi, b := range s.branches {
			isSel, isExp := false, false
			for idx, it := range items {
				if it.si == si && it.bi == bi {
					isSel = idx == m.cursor
					isExp = idx == m.expanded
					break
				}
			}
			short := branchShort(b.name)
			cur := "  "
			if isSel {
				cur = " " + sty.Render(">")
			}

			switch b.state {
			case bsMerged:
				nm := dimS.Render(short)
				if isSel {
					nm = fgS.Render(short)
				}
				lft := fmt.Sprintf("%s %s %s", cur, greenS.Render("✓"), nm)
				rt := dimS.Render(fmt.Sprintf("%d→1  merged day %d  #%d", b.origCount, b.day, b.pr))
				lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
			case bsActive:
				nm := fgS.Render(short)
				if isSel {
					nm = lipgloss.NewStyle().Bold(true).Foreground(s.color).Render(short)
				}
				lft := fmt.Sprintf("%s %s %s", cur, accentS.Render("●"), nm)
				info := fgS.Render(fmt.Sprintf("working · %d commits", len(b.commits)))
				latest := dimS.Render("latest: " + b.commits[len(b.commits)-1].age)
				rt := info + "  " + latest
				lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
				if isExp {
					lines = append(lines, m.renderCommitBox(b, s.color)...)
				}
			case bsBlocked:
				nm := fgS.Render(short)
				if isSel {
					nm = boldS.Render(short)
				}
				lft := fmt.Sprintf("%s %s %s", cur, redS.Render("⏸"), nm)
				rt := dimS.Render("blocked ← ") + dimS.Render(b.blockOn)
				lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
			case bsQueued:
				nm := dimS.Render(short)
				if isSel {
					nm = fgS.Render(short)
				}
				lft := fmt.Sprintf("%s %s %s", cur, dimS.Render("○"), nm)
				rt := dimS.Render("queued ← " + b.blockOn)
				lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
			}
		}
	}
	return lipgloss.NewStyle().Width(m.width).Height(h).Render(strings.Join(lines, "\n"))
}

func (m model) renderCommitBox(b branch, stackColor lipgloss.AdaptiveColor) []string {
	var lines []string
	bw := minI(m.width-6, 72)
	if bw < 40 {
		bw = 40
	}
	ind := "     "
	d := dimS.Render
	lines = append(lines, ind+d("┌"+strings.Repeat("─", bw-2)+"┐"))
	for _, c := range b.commits {
		iw := bw - 4
		age := dimS.Render(c.age)
		mw := iw - len(c.hash) - lipgloss.Width(c.age) - 6
		msg := c.msg
		if len(msg) > mw && mw > 3 {
			msg = msg[:mw-2] + ".."
		}
		cl := padR(fmt.Sprintf("  %s  %s", magS.Render(c.hash), msg), iw-lipgloss.Width(c.age)) + age
		lines = append(lines, ind+d("│")+cl+d(" │"))
	}
	lines = append(lines, ind+d("├"+strings.Repeat("─", bw-2)+"┤"))
	si := dimS.Render("○")
	sl := dimS.Render("not yet")
	if b.submitted {
		si = greenS.Render("✓")
		sl = lipgloss.NewStyle().Foreground(stackColor).Render("submitted")
	}
	pi := dimS.Render("—")
	pl := dimS.Render("no PR")
	if b.published {
		pi = greenS.Render("●")
		pl = greenS.Render(fmt.Sprintf("PR #%d", b.pr))
	}
	st := padR(fmt.Sprintf("  submit: %s %s     publish: %s %s", si, sl, pi, pl), bw-2)
	lines = append(lines, ind+d("│")+st+d("│"))
	lines = append(lines, ind+d("└"+strings.Repeat("─", bw-2)+"┘"))
	return lines
}

// ═══════════════════════════════════════════════════════════════════
// STREAMS VIEW — 3-level drill-down
// ═══════════════════════════════════════════════════════════════════

func (m model) updateStreams(k string) model {
	switch m.streamLvl {
	case lvOverview:
		return m.updateStreamsL1(k)
	case lvTask:
		return m.updateStreamsL2(k)
	case lvAgent:
		return m.updateStreamsL3(k)
	}
	return m
}

func (m model) viewStreams(h int) string {
	switch m.streamLvl {
	case lvOverview:
		return m.viewStreamsL1(h)
	case lvTask:
		return m.viewStreamsL2(h)
	case lvAgent:
		return m.viewStreamsL3(h)
	}
	return ""
}

// --- Level 1: Task Overview ---

func (m model) updateStreamsL1(k string) model {
	switch k {
	case "j", "down":
		if m.taskCur < len(m.tasks)-1 {
			m.taskCur++
		}
	case "k", "up":
		if m.taskCur > 0 {
			m.taskCur--
		}
	case "enter":
		m.streamLvl = lvTask
		m.agentCur = 0
	case "1", "2", "3":
		idx, _ := strconv.Atoi(k)
		idx--
		if idx >= 0 && idx < len(m.tasks) {
			m.taskCur = idx
		}
	}
	return m
}

func (m model) viewStreamsL1(h int) string {
	var lines []string
	tL := boldS.Render(" STREAMS")
	tR := dimS.Render(fmt.Sprintf("%d task sessions", len(m.tasks)))
	lines = append(lines, padR(tL, m.width-lipgloss.Width(tR))+tR)
	lines = append(lines, dimS.Render(" "+strings.Repeat("═", m.width-2)))

	for i, t := range m.tasks {
		sel := i == m.taskCur
		lines = append(lines, "")
		cur := " "
		if sel {
			cur = ">"
		}
		nm := fgS.Render(t.id + " " + t.title)
		if sel {
			nm = boldS.Render(t.id + " " + t.title)
		}
		lft := fmt.Sprintf(" %s %s %s", cur, accentS.Render("●"), nm)
		rt := dimS.Render(t.branch)
		lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
		lines = append(lines, " "+dimS.Render(strings.Repeat("─", m.width-2)))

		// Phase pipeline
		pipe := "   " + dimS.Render(t.loopName+"   ") + renderPipeline(t.phases)
		lines = append(lines, pipe)

		// Active agent + stats
		activeAgent := ""
		for _, ag := range t.agents {
			if ag.status == agActive {
				activeAgent = ag.name + " (" + ag.model + ")"
				break
			}
		}
		fc := 0
		for _, ag := range t.agents {
			fc += len(ag.files)
		}
		aL := "   " + dimS.Render("Active: ") + accentS.Render(activeAgent)
		aR := dimS.Render(fmt.Sprintf("%d files  %s tok  %s", fc, t.tokens, t.elapsed))
		lines = append(lines, padR(aL, m.width-lipgloss.Width(aR))+aR)
	}

	return lipgloss.NewStyle().Width(m.width).Height(h).Render(strings.Join(lines, "\n"))
}

// --- Level 2: Task Detail ---

func (m model) updateStreamsL2(k string) model {
	t := m.tasks[m.taskCur]
	switch k {
	case "j", "down":
		if m.agentCur < len(t.agents)-1 {
			m.agentCur++
		}
	case "k", "up":
		if m.agentCur > 0 {
			m.agentCur--
		}
	case "enter":
		m.streamLvl = lvAgent
		m.msgScroll = 0
		m.agentPane = 0
		m.fileCursor = 0
		m.toolsExpanded = true
	case "esc":
		m.streamLvl = lvOverview
	case "1", "2", "3", "4":
		idx, _ := strconv.Atoi(k)
		idx--
		if idx >= 0 && idx < len(t.agents) {
			m.agentCur = idx
		}
	}
	return m
}

func (m model) viewStreamsL2(h int) string {
	t := m.tasks[m.taskCur]
	var lines []string

	// Header
	tL := " " + boldS.Render(t.id+" "+t.title)
	tR := dimS.Render(t.loopName+"  "+t.elapsed)
	lines = append(lines, padR(tL, m.width-lipgloss.Width(tR))+tR)
	bL := " " + dimS.Render("branch: "+t.branch)
	bR := dimS.Render(t.tokens+" tokens")
	lines = append(lines, padR(bL, m.width-lipgloss.Width(bR))+bR)
	lines = append(lines, dimS.Render(" "+strings.Repeat("═", m.width-2)))

	// Phase pipeline (wide)
	lines = append(lines, "")
	lines = append(lines, " "+renderPipelineWide(t.phases, m.width-2))
	lines = append(lines, "")

	// Agent roster
	lines = append(lines, " "+boldS.Render("AGENTS"))
	for i, ag := range t.agents {
		sel := i == m.agentCur
		var icon string
		switch ag.status {
		case agDone:
			icon = greenS.Render("✓")
		case agActive:
			icon = accentS.Render("●")
		case agWaiting:
			icon = dimS.Render("○")
		}
		cur := " "
		if sel {
			cur = ">"
		}
		nm := fgS.Render(ag.name)
		if sel && ag.status == agActive {
			nm = boldS.Render(ag.name)
		}
		if ag.status == agWaiting {
			nm = dimS.Render(ag.name)
		}
		tok := dimS.Render(ag.tokens)
		if ag.tokens == "" {
			tok = dimS.Render("—")
		}
		dur := dimS.Render(ag.duration)
		if ag.duration == "" {
			dur = dimS.Render("—")
		}
		sum := dimS.Render(ag.summary)
		if ag.status == agActive {
			sum = accentS.Render(ag.summary)
		}
		lft := fmt.Sprintf(" %s %s %-14s %-10s %s  %s", cur, icon, nm, dimS.Render(ag.model), padR(tok, 8), padR(dur, 8))
		lines = append(lines, padR(lft, m.width-lipgloss.Width(sum))+sum)
	}

	// Files touched
	lines = append(lines, "")
	allFiles := aggregateFiles(t)
	lines = append(lines, " "+boldS.Render(fmt.Sprintf("FILES TOUCHED (%d)", len(allFiles))))
	for _, f := range allFiles {
		adds := greenS.Render(fmt.Sprintf("+%d", f.added))
		dels := dimS.Render(fmt.Sprintf("-%d", f.removed))
		if f.removed > 0 {
			dels = redS.Render(fmt.Sprintf("-%d", f.removed))
		}
		lft := "   " + dimS.Render(f.path)
		rt := adds + "  " + dels
		lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
	}

	// Summary
	lines = append(lines, "")
	for _, ag := range t.agents {
		if ag.status == agActive {
			lines = append(lines, " "+boldS.Render("SUMMARY"))
			lines = append(lines, "   "+fgS.Render(ag.summary))
			break
		}
	}

	return lipgloss.NewStyle().Width(m.width).Height(h).Render(strings.Join(lines, "\n"))
}

// --- Level 3: Agent Detail ---

func (m model) updateStreamsL3(k string) model {
	ag := m.tasks[m.taskCur].agents[m.agentCur]
	switch k {
	case "j", "down":
		if m.agentPane == 0 {
			m.msgScroll++
		} else {
			if m.fileCursor < len(ag.files)-1 {
				m.fileCursor++
			}
		}
	case "k", "up":
		if m.agentPane == 0 {
			if m.msgScroll > 0 {
				m.msgScroll--
			}
		} else {
			if m.fileCursor > 0 {
				m.fileCursor--
			}
		}
	case "enter":
		if m.agentPane == 0 {
			m.toolsExpanded = !m.toolsExpanded
		}
	case "esc":
		m.streamLvl = lvTask
		m.toolsExpanded = true
	}
	return m
}

func (m model) viewStreamsL3(h int) string {
	t := m.tasks[m.taskCur]
	ag := t.agents[m.agentCur]
	var lines []string

	// Header
	tL := " " + boldS.Render(t.id) + " " + dimS.Render("›") + " " + accentS.Render(ag.name) + " " + dimS.Render("("+ag.model+")")
	tR := dimS.Render(ag.tokens+" tok  "+ag.duration)
	lines = append(lines, padR(tL, m.width-lipgloss.Width(tR))+tR)
	lines = append(lines, dimS.Render(" "+strings.Repeat("═", m.width-2)))

	// Pane tabs
	msgTab := "Messages"
	fileTab := "Files"
	if m.agentPane == 0 {
		msgTab = "[" + msgTab + "]"
	} else {
		fileTab = "[" + fileTab + "]"
	}
	pL := " " + accentS.Render(msgTab) + "  " + dimS.Render(fileTab)
	if m.agentPane == 1 {
		pL = " " + dimS.Render(msgTab) + "  " + accentS.Render(fileTab)
	}
	pR := dimS.Render(ag.summary)
	lines = append(lines, padR(pL, m.width-lipgloss.Width(pR))+pR)
	lines = append(lines, " "+dimS.Render(strings.Repeat("─", m.width-2)))
	lines = append(lines, "")

	if m.agentPane == 0 {
		lines = append(lines, m.renderMessages(ag, h-6)...)
	} else {
		lines = append(lines, m.renderFilesPane(ag, h-6)...)
	}

	return lipgloss.NewStyle().Width(m.width).Height(h).Render(strings.Join(lines, "\n"))
}

func (m model) renderMessages(ag taskAgent, maxH int) []string {
	var all []string
	for _, msg := range ag.messages {
		header := boldS.Render(strings.ToUpper(msg.role))
		all = append(all, " "+header)
		for _, line := range strings.Split(msg.content, "\n") {
			all = append(all, " "+dimS.Render("│")+" "+fgS.Render(line))
		}
		all = append(all, "")
		for _, tc := range msg.tools {
			all = append(all, m.renderToolCall(tc)...)
			all = append(all, "")
		}
	}

	// Apply scroll
	if m.msgScroll >= len(all) {
		m.msgScroll = maxI(0, len(all)-1)
	}
	start := m.msgScroll
	end := minI(start+maxH, len(all))
	if start >= end {
		return []string{dimS.Render("   (no messages)")}
	}
	return all[start:end]
}

func (m model) renderToolCall(tc toolCall) []string {
	var lines []string
	arrow := dimS.Render("▸")
	if m.toolsExpanded && len(tc.diffLines) > 0 {
		arrow = accentS.Render("▾")
	}

	icon := dimS.Render(tc.kind.String())
	switch tc.kind {
	case tkRead:
		icon = dimS.Render("Read")
	case tkEdit:
		icon = accentS.Render("Edit")
	case tkBash:
		icon = magS.Render("Bash")
	case tkGrep:
		icon = dimS.Render("Grep")
	}

	lft := fmt.Sprintf("   %s %s  %s", arrow, icon, dimS.Render(tc.target))
	rt := dimS.Render(tc.duration)
	lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)

	if tc.result != "" {
		lines = append(lines, "     "+dimS.Render(tc.result))
	}

	if m.toolsExpanded && len(tc.diffLines) > 0 {
		bw := minI(m.width-8, 60)
		lines = append(lines, "     "+dimS.Render("┌"+strings.Repeat("─", bw)+"┐"))
		for _, dl := range tc.diffLines {
			styled := dimS.Render(dl)
			if strings.HasPrefix(dl, "+") {
				styled = greenS.Render(dl)
			} else if strings.HasPrefix(dl, "-") {
				styled = redS.Render(dl)
			}
			pad := bw - len(dl)
			if pad < 0 {
				pad = 0
			}
			lines = append(lines, "     "+dimS.Render("│")+" "+styled+strings.Repeat(" ", pad)+dimS.Render("│"))
		}
		lines = append(lines, "     "+dimS.Render("└"+strings.Repeat("─", bw)+"┘"))
	}

	return lines
}

func (m model) renderFilesPane(ag taskAgent, maxH int) []string {
	var lines []string
	for i, f := range ag.files {
		cur := " "
		if i == m.fileCursor {
			cur = ">"
		}
		nm := dimS.Render(f.path)
		if i == m.fileCursor {
			nm = fgS.Render(f.path)
		}
		adds := greenS.Render(fmt.Sprintf("+%d", f.added))
		dels := dimS.Render(fmt.Sprintf("-%d", f.removed))
		if f.removed > 0 {
			dels = redS.Render(fmt.Sprintf("-%d", f.removed))
		}
		lft := fmt.Sprintf(" %s %s", cur, nm)
		rt := adds + "  " + dels
		lines = append(lines, padR(lft, m.width-lipgloss.Width(rt))+rt)
	}

	// Show diff for selected file
	if m.fileCursor < len(ag.files) {
		f := ag.files[m.fileCursor]
		lines = append(lines, "")
		lines = append(lines, " "+dimS.Render("─── "+f.path+" "+strings.Repeat("─", maxI(0, m.width-len(f.path)-8))))
		for _, line := range f.hunks {
			styled := dimS.Render(line)
			if strings.HasPrefix(line, "+") {
				styled = greenS.Render(line)
			} else if strings.HasPrefix(line, "-") {
				styled = redS.Render(line)
			}
			lines = append(lines, " "+styled)
		}
	}
	return lines
}

// ═══════════════════════════════════════════════════════════════════
// Pipeline renderers
// ═══════════════════════════════════════════════════════════════════

func renderPipeline(phases []taskPhase) string {
	var parts []string
	for i, p := range phases {
		var icon, label string
		switch p.status {
		case phDone:
			icon = greenS.Render("✓")
			label = greenS.Render(p.name)
		case phActive:
			icon = accentS.Render("●")
			label = accentS.Render(p.name)
		case phWaiting:
			icon = dimS.Render("○")
			label = dimS.Render(p.name)
		}
		parts = append(parts, label+" "+icon)
		if i < len(phases)-1 {
			conn := dimS.Render(" → ")
			if p.status == phDone {
				conn = greenS.Render(" → ")
			}
			parts = append(parts, conn)
		}
	}
	return strings.Join(parts, "")
}

func renderPipelineWide(phases []taskPhase, w int) string {
	n := len(phases)
	if n == 0 {
		return ""
	}
	connW := maxI(2, (w-n*12)/(n-1))
	var parts []string
	for i, p := range phases {
		var icon, label string
		switch p.status {
		case phDone:
			icon = greenS.Render("✓")
			label = greenS.Render(p.name)
		case phActive:
			icon = accentS.Render("●")
			label = accentS.Render(p.name)
		case phWaiting:
			icon = dimS.Render("○")
			label = dimS.Render(p.name)
		}
		parts = append(parts, label+" "+icon)
		if i < n-1 {
			conn := dimS.Render(" " + strings.Repeat("─", connW) + " ")
			if p.status == phDone {
				conn = greenS.Render(" " + strings.Repeat("─", connW) + " ")
			}
			parts = append(parts, conn)
		}
	}
	return strings.Join(parts, "")
}

func aggregateFiles(t taskSession) []fileDiff {
	seen := map[string]*fileDiff{}
	var order []string
	for _, ag := range t.agents {
		for _, f := range ag.files {
			if _, ok := seen[f.path]; !ok {
				seen[f.path] = &fileDiff{path: f.path}
				order = append(order, f.path)
			}
			seen[f.path].added += f.added
			seen[f.path].removed += f.removed
		}
	}
	var result []fileDiff
	for _, p := range order {
		result = append(result, *seen[p])
	}
	return result
}

// ═══════════════════════════════════════════════════════════════════
// CHAT VIEW
// ═══════════════════════════════════════════════════════════════════

func (m model) viewChat(h int) string {
	items := m.navItems()
	ctx := "no context"
	ctxColor := colorAccent
	if m.cursor < len(items) {
		ni := items[m.cursor]
		s := m.project.stacks[ni.si]
		b := s.branches[ni.bi]
		ctx = s.name + " / " + branchShort(b.name)
		ctxColor = s.color
	}
	var lines []string
	lines = append(lines, " "+dimS.Render("context: ")+lipgloss.NewStyle().Foreground(ctxColor).Render(ctx))
	lines = append(lines, "")
	for _, msg := range m.chatMsgs {
		lines = append(lines, "  "+dimS.Render(msg))
	}
	return lipgloss.NewStyle().Width(m.width).Height(h).Render(strings.Join(lines, "\n"))
}

// ═══════════════════════════════════════════════════════════════════
// FAKE DATA
// ═══════════════════════════════════════════════════════════════════

func fakeProject() proj {
	return proj{
		name: "Auth System Overhaul", day: 3, totalDays: 5,
		stacks: []stack{
			{
				name: "db-migration", archived: true, doneDay: 1,
				color: lipgloss.AdaptiveColor{Light: "#999999", Dark: "#6272A4"},
				branches: []branch{
					{name: "dug/db-migration/1-schema-setup", state: bsMerged, day: 0, origCount: 2, pr: 1},
					{name: "dug/db-migration/2-seed-data", state: bsMerged, day: 1, origCount: 3, pr: 3},
				},
			},
			{
				name: "session-mgmt",
				color: lipgloss.AdaptiveColor{Light: "#00695C", Dark: "#8BE9FD"},
				branches: []branch{
					{name: "dug/session-mgmt/1-token-model", state: bsMerged, day: 1, origCount: 3, pr: 4},
					{name: "dug/session-mgmt/2-session-store", state: bsMerged, day: 2, origCount: 5, pr: 7},
					{name: "dug/session-mgmt/3-session-api", state: bsActive, day: 3,
						commits: []commit{
							{hash: "a1b2c3d", msg: "Add session validation endpoint", age: "12m"},
							{hash: "e4f5g6h", msg: "Wire session middleware", age: "8m"},
							{hash: "i7j8k9l", msg: "Add session refresh logic", age: "3m"},
							{hash: "m1n2o3p", msg: "Fix concurrent session handling", age: "now"},
						},
					},
				},
			},
			{
				name: "jwt-middleware",
				color: lipgloss.AdaptiveColor{Light: "#2E7D32", Dark: "#50FA7B"},
				deps:  []string{"session-mgmt"},
				branches: []branch{
					{name: "dug/jwt-middleware/1-jwt-utils", state: bsMerged, day: 2, origCount: 2, pr: 9},
					{name: "dug/jwt-middleware/2-auth-middleware", state: bsBlocked, blockOn: "session-mgmt/3-session-api"},
				},
			},
			{
				name: "api-keys",
				color: lipgloss.AdaptiveColor{Light: "#E65100", Dark: "#FFB86C"},
				deps:  []string{"session-mgmt", "jwt-middleware"},
				branches: []branch{
					{name: "dug/api-keys/1-key-model", state: bsQueued, blockOn: "jwt-middleware/2-auth-middleware"},
					{name: "dug/api-keys/2-key-endpoints", state: bsQueued, blockOn: "api-keys/1-key-model"},
				},
			},
		},
	}
}

func fakeTasks() []taskSession {
	return []taskSession{
		{
			id: "SB-042", title: "Session API", branch: "session-mgmt/3-session-api",
			loopName: "/plan_w_team", tokens: "8.1k", elapsed: "4m 22s",
			phases: []taskPhase{
				{"architect", phDone}, {"review", phDone}, {"build", phActive}, {"validate", phWaiting},
			},
			agents: []taskAgent{
				{
					name: "Architect", status: agDone, model: "opus-4", tokens: "1.2k", duration: "45s",
					summary: "Designed session validation flow",
					messages: []agentMsg{
						{role: "thought", content: "I need to understand the session domain.\nLet me read the existing models and service layer."},
						{role: "response", content: "Session domain has 3 core entities.\nDesigning validation flow with 4 endpoints.",
							tools: []toolCall{
								{kind: tkRead, target: "features/sessions/models.py", result: "Session EventPattern with 6 fields", duration: "85ms"},
								{kind: tkRead, target: "features/sessions/service.py", result: "SessionService: create, get, list, transition", duration: "62ms"},
							}},
					},
					files: []fileDiff{},
				},
				{
					name: "Reviewer", status: agDone, model: "opus-4", tokens: "2.1k", duration: "1m 12s",
					summary: "Approved with minor feedback",
					messages: []agentMsg{
						{role: "thought", content: "Reviewing the architect's spec for completeness.\nChecking error handling and edge cases."},
						{role: "response", content: "Architecture looks solid. Two suggestions:\n1. Add rate limiting to refresh endpoint\n2. Use sliding window for token expiry",
							tools: []toolCall{
								{kind: tkRead, target: "features/sessions/models.py", result: "Verified field definitions", duration: "45ms"},
								{kind: tkGrep, target: "error_handler pattern in organisms/", result: "Found 3 existing error handlers", duration: "120ms"},
							}},
					},
					files: []fileDiff{},
				},
				{
					name: "Builder", status: agActive, model: "opus-4", tokens: "4.2k", duration: "2m 15s",
					summary: "Implementing endpoints (3/4 done)",
					messages: []agentMsg{
						{role: "thought", content: "Starting implementation. Need to read existing models\nand understand the service interface.",
							tools: []toolCall{
								{kind: tkRead, target: "features/sessions/models.py", result: "Session model with state machine: active/expired/revoked", duration: "85ms"},
								{kind: tkRead, target: "features/sessions/service.py", result: "SessionService with CRUD + transition methods", duration: "62ms"},
							}},
						{role: "response", content: "Creating REST router with 4 endpoints:\ncreate, get, list, and refresh.",
							tools: []toolCall{
								{kind: tkEdit, target: "organisms/rest/sessions.py", result: "+38 lines — router with create/get/list", duration: "210ms",
									diffLines: []string{
										"+ from fastapi import APIRouter, Depends",
										"+ from features.sessions.service import SessionService",
										"+ ",
										"+ router = APIRouter(prefix=\"/sessions\")",
										"+ ",
										"+ @router.post(\"/\")",
										"+ async def create_session(data: SessionCreate):",
										"+     return await service.create(db, data)",
									}},
								{kind: tkBash, target: "just test -- -k test_session", result: "3 passed, 0 failed", duration: "1.2s"},
							}},
						{role: "thought", content: "3 endpoints passing. Now implementing refresh.",
							tools: []toolCall{
								{kind: tkEdit, target: "organisms/rest/sessions.py", result: "+12 lines — refresh endpoint", duration: "180ms",
									diffLines: []string{
										"+ @router.post(\"/{id}/refresh\")",
										"+ async def refresh_session(",
										"+     id: UUID,",
										"+     db: AsyncSession = Depends(get_db),",
										"+ ):",
										"+     return await service.refresh(db, id)",
									}},
							}},
					},
					files: []fileDiff{
						{path: "organisms/rest/sessions.py", added: 38, removed: 0, hunks: []string{
							"+ from fastapi import APIRouter, Depends, HTTPException",
							"+ from features.sessions.service import SessionService",
							"+ from features.sessions.models import SessionCreate",
							"+ ",
							"+ router = APIRouter(prefix=\"/sessions\", tags=[\"sessions\"])",
							"+ ",
							"+ @router.post(\"/\", response_model=SessionResponse)",
							"+ async def create_session(",
							"+     data: SessionCreate,",
							"+     db: AsyncSession = Depends(get_db),",
							"+ ):",
							"+     service = SessionService()",
							"+     return await service.create(db, data)",
						}},
						{path: "features/sessions/models.py", added: 2, removed: 1, hunks: []string{
							"+ from patterns.fields import StateField",
							"+ STATES = [\"active\", \"expired\", \"revoked\"]",
							"- STATES = [\"active\", \"expired\"]",
						}},
						{path: "molecules/session_workflow.py", added: 15, removed: 4, hunks: []string{
							"+ async def refresh_session(self, db, session_id):",
							"+     session = await self.get(db, session_id)",
							"+     if session.state != \"active\":",
							"+         raise ValueError(\"Cannot refresh\")",
							"+     new_token = generate_token()",
							"+     session.token_hash = hash_token(new_token)",
							"+     session.expires_at = utcnow() + timedelta(hours=24)",
							"+     await db.commit()",
							"+     return new_token",
							"- async def refresh_session(self, db, sid):",
							"-     raise NotImplementedError(\"TODO\")",
						}},
						{path: "tests/test_session_api.py", added: 72, removed: 0, hunks: []string{
							"+ import pytest",
							"+ from httpx import AsyncClient",
							"+ ",
							"+ @pytest.mark.asyncio",
							"+ async def test_create_session(client):",
							"+     resp = await client.post(\"/sessions/\")",
							"+     assert resp.status_code == 201",
						}},
					},
				},
				{
					name: "Validator", status: agWaiting, model: "sonnet-4",
					summary: "Waiting for Builder to finish",
					messages: []agentMsg{},
					files:    []fileDiff{},
				},
			},
		},
		{
			id: "SB-043", title: "Token Refresh", branch: "jwt-middleware/2-auth-middleware",
			loopName: "/develop", tokens: "2.4k", elapsed: "1m 50s",
			phases: []taskPhase{
				{"understand", phDone}, {"plan", phDone}, {"implement", phActive}, {"test", phWaiting},
			},
			agents: []taskAgent{
				{
					name: "Understander", status: agDone, model: "sonnet-4", tokens: "800", duration: "30s",
					summary: "Read existing token refresh logic",
					messages: []agentMsg{
						{role: "thought", content: "Reading the current token handling code."},
						{role: "response", content: "Token service uses simple expiry. No rotation.",
							tools: []toolCall{
								{kind: tkRead, target: "molecules/auth/token_service.py", result: "TokenService with issue/verify methods", duration: "70ms"},
								{kind: tkGrep, target: "refresh pattern in molecules/auth/", result: "No existing refresh implementation", duration: "90ms"},
							}},
					},
					files: []fileDiff{},
				},
				{
					name: "Planner", status: agDone, model: "opus-4", tokens: "1.1k", duration: "40s",
					summary: "Planned token rotation strategy",
					messages: []agentMsg{
						{role: "response", content: "Plan: Add sliding window rotation.\n1. New refresh_token field on TokenModel\n2. Rotation on each refresh call\n3. Revoke old token on rotation",
							tools: []toolCall{
								{kind: tkRead, target: "features/auth/models.py", result: "TokenModel with hash, expiry fields", duration: "55ms"},
							}},
					},
					files: []fileDiff{},
				},
				{
					name: "Implementer", status: agActive, model: "sonnet-4", tokens: "500", duration: "40s",
					summary: "Adding token rotation to refresh",
					messages: []agentMsg{
						{role: "thought", content: "Implementing the rotation strategy from the plan.",
							tools: []toolCall{
								{kind: tkRead, target: "molecules/auth/token_service.py", result: "Current service, no rotation", duration: "60ms"},
							}},
						{role: "response", content: "Adding refresh_token rotation method.",
							tools: []toolCall{
								{kind: tkEdit, target: "molecules/auth/token_service.py", result: "+22 lines — rotation logic", duration: "150ms",
									diffLines: []string{
										"+ async def rotate_token(self, db, token):",
										"+     old = await self.verify(token)",
										"+     new_token = self.generate()",
										"+     old.revoked_at = utcnow()",
										"+     await db.commit()",
										"+     return new_token",
									}},
							}},
					},
					files: []fileDiff{
						{path: "molecules/auth/token_service.py", added: 22, removed: 8, hunks: []string{
							"+ async def rotate_token(self, db, token):",
							"+     old = await self.verify(token)",
							"+     new_token = self.generate()",
							"+     old.revoked_at = utcnow()",
							"+     await db.commit()",
							"+     return new_token",
							"- # TODO: implement rotation",
						}},
						{path: "tests/test_token_rotation.py", added: 15, removed: 0, hunks: []string{
							"+ async def test_rotate_token(client):",
							"+     token = await create_token()",
							"+     new = await client.post(\"/auth/refresh\")",
							"+     assert new.status_code == 200",
						}},
					},
				},
				{
					name: "Tester", status: agWaiting, model: "sonnet-4",
					summary: "Waiting for implementation",
					messages: []agentMsg{},
					files:    []fileDiff{},
				},
			},
		},
	}
}

// ═══════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════

func branchShort(name string) string {
	parts := strings.Split(name, "/")
	return parts[len(parts)-1]
}

func progressBar(pct, w int) string {
	if w < 5 {
		w = 5
	}
	f := w * pct / 100
	e := w - f
	return accentS.Render(strings.Repeat("█", f)) + dimS.Render(strings.Repeat("░", e))
}

func padR(s string, w int) string {
	v := lipgloss.Width(s)
	if v >= w {
		return s
	}
	return s + strings.Repeat(" ", w-v)
}

func minI(a, b int) int {
	if a < b {
		return a
	}
	return b
}
func maxI(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// ═══════════════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════════════

func main() {
	dump := flag.String("dump", "", "Dump: stacks, streams, streams:task, streams:agent, chat")
	flag.Parse()

	if *dump != "" {
		lipgloss.SetColorProfile(termenv.TrueColor)
		m := initialModel()
		args := flag.Args()
		if len(args) >= 1 {
			fmt.Sscanf(args[0], "%d", &m.width)
		}
		if len(args) >= 2 {
			fmt.Sscanf(args[1], "%d", &m.height)
		}

		parts := strings.SplitN(*dump, ":", 2)
		switch parts[0] {
		case "stacks":
			m.tab = tabStacks
		case "streams":
			m.tab = tabStreams
			if len(parts) > 1 {
				switch parts[1] {
				case "task":
					m.streamLvl = lvTask
				case "agent":
					m.streamLvl = lvAgent
					m.agentCur = 2 // Builder
					m.toolsExpanded = true
				}
			}
		case "chat":
			m.tab = tabChat
		default:
			fmt.Fprintf(os.Stderr, "unknown: %s\n", *dump)
			os.Exit(1)
		}
		fmt.Println(m.View())
		return
	}

	p := tea.NewProgram(initialModel(), tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
