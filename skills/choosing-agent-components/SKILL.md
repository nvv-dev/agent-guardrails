---
name: choosing-agent-components
description: Use when deciding how to add a new capability or rule to a Claude Code setup — "should this be a skill, a subagent, a hook, an MCP server, a slash command or just a line in CLAUDE.md?". Picks the lightest piece that does the job, to keep context and token costs low.
disable-model-invocation: true
---

# Choosing the lightest agent component

Every piece has a cost: always-loaded text costs tokens in every message; subagents cost a new context; MCP servers add tool schemas. Pick the cheapest piece that reliably does the job.

## Decision order (stop at the first that fits)

1. **Nothing.** The model already does it well when asked plainly. Write a better prompt, not a component.
2. **A deterministic tool** (linter rule, formatter, test, CI check, script). If a rule can be checked by code, do not ask the model to remember it.
3. **A hook.** The behavior must *always* or *never* happen regardless of what the model decides (block a command, run a formatter after edits, scan on commit). Hooks enforce; instructions only ask.
4. **A line in `CLAUDE.md`.** A short rule that applies to almost every task in the repo (code language, branch naming, "verify APIs before using them"). Keep the file short; it is paid on every message.
5. **A skill.** Knowledge or a procedure needed only for some tasks (a review rubric, a deploy checklist). Its description is always loaded; its body only when used. Heavy or rare skills: `disable-model-invocation: true`.
6. **A slash command.** A procedure the human triggers by name, with arguments.
7. **A subagent.** Work that needs a separate context: reviewing code it did not write, exploring many files and returning only a conclusion, or a role with restricted tools.
8. **An MCP server.** Access to an external system (an API, a database, a SaaS) that no CLI covers well. Prefer an existing CLI driven from Bash when one exists; it usually costs fewer tokens.
9. **A plugin.** A bundle of the above to share across repositories or people.

## Checks before building

- Does an existing component already cover it? Extend it rather than adding a parallel one.
- Who maintains it, and how will you know it broke? Add a test or a "Known failures" section.
- Does it need secrets or network? Then it needs a security review (`vetting-external-skills` applies to your own components too).

## Output

The chosen piece, why the lighter options do not fit, and the file skeleton to create.

## Known failures

_Record real mistakes here with a date and the rule that prevents them._
