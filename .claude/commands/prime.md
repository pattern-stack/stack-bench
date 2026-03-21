Load project context for this session.

Run these commands and internalize the results:

1. Read the root CLAUDE.md: `cat CLAUDE.md`
2. Read SDLC config: `cat .claude/sdlc.yml`
3. List all tracked files: `git ls-files`
4. Check current branch and recent commits: `git log --oneline -20`
5. Check for any uncommitted work: `git status`
6. Check stack status: `stack status` (if available)
7. Check for active work: look at `docs/issues/` for in-progress issues

## Skills & Commands Inventory

After loading project context, also catalog what's available:

8. List available skills: `ls .claude/skills/*/SKILL.md`
9. List available commands: `ls .claude/commands/*.md`
10. List available agents: `ls .claude/agents/team/*.md`

## Summary

After loading, provide a brief summary:
- Current branch and recent activity
- Any uncommitted changes
- Active issues (in-progress status)
- Key architectural notes from CLAUDE.md and sdlc.yml
- Available skills, commands, and agents

Keep the summary to 10-15 lines. You are now primed and ready to work.
