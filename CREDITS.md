# Credits

Written from scratch. Ideas came from:

- Destructive-command hooks: [garrytan/gstack](https://github.com/garrytan/gstack) (/careful, /freeze, /guard) and [mattpocock/skills](https://github.com/mattpocock/skills) (git-guardrails-claude-code).
- Vetting third-party agent code: [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) (Apache-2.0, used as an external tool, not bundled); lockfile with pinned versions inspired by [vercel-labs/skills](https://github.com/vercel-labs/skills); attribution practice for adapted third-party skills from [Hainrixz/claude-webkit](https://github.com/Hainrixz/claude-webkit).
- Choosing the lightest component: [Hainrixz/claude-anatomy](https://github.com/Hainrixz/claude-anatomy).
- Context-hygiene rules in the CLAUDE.md template: [shanraisshan/claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) and [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient) (rules against guessing and about file reads; we did not adopt its compressed profile or its auto-commit hook).
