# agent-guardrails

Seguridad y gobierno para agentes de código. Un perfil de agente *pide* que no se haga algo; un hook lo *impide*. Este repo trae las dos cosas, más las plantillas para dejar un repo listo para trabajar con agentes.

*English version below.*

## Qué incluye

| Pieza | Qué hace |
|---|---|
| [hooks/block_destructive.py](hooks/block_destructive.py) | Hook `PreToolUse` que **bloquea** comandos irreversibles (`rm -rf /`, push forzado, `--no-verify`, `DROP TABLE`, `terraform destroy`, leer `.env`, `curl … \| sh`…) y **pide aprobación** para los riesgosos (`git reset --hard`, push a `main`, `kubectl delete`, `sudo`, `ansible-playbook` sin `--check`…). Con 60+ casos de prueba. |
| [skills/vetting-external-skills](skills/vetting-external-skills/SKILL.md) | Proceso para evaluar una skill, plugin o MCP de terceros: leer, escanear con SkillSpector, decidir, fijar por commit y registrar. |
| [skills/choosing-agent-components](skills/choosing-agent-components/SKILL.md) | Decide si algo debe ser regla de linter, hook, línea de CLAUDE.md, skill, comando, subagente, MCP o plugin: la pieza más liviana que funcione. |
| [templates/CLAUDE.md](templates/CLAUDE.md) | Reglas compartidas: dueño que aprueba, idioma, forma de trabajar, higiene de contexto (menos tokens) y seguridad. |
| [templates/settings.json](templates/settings.json) | Permisos de Claude Code que impiden leer secretos y piden aprobación para `git push` y SSH. |
| [templates/skills-lock.json](templates/skills-lock.json) | Registro de cada skill externa con fuente, commit, licencia, resultado del escaneo y decisión. |
| [templates/pre-commit-config.yaml](templates/pre-commit-config.yaml) | gitleaks y chequeos básicos antes de cada commit; bloquea commits directos a `main`. |
| [templates/github-workflows/skill-scan.yml](templates/github-workflows/skill-scan.yml) | CI que pasa SkillSpector por cada skill, agente y hook del repo. |

## Instalación

**Como plugin** (activa el hook en todos tus repos):

```text
/plugin marketplace add nvv-dev/claude-plugins
/plugin install agent-guardrails@nvvdev
```

**Sin plugin:** copia `hooks/block_destructive.py` a `.claude/hooks/` de tu repo y registra el hook en `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/block_destructive.py\"", "timeout": 10 }] }
    ]
  }
}
```

Requiere Python 3.9 o superior, sin dependencias.

## Adaptar las reglas

Edita `DENY_RULES` y `ASK_RULES` en el hook y agrega un caso en `tests/test_block_destructive.py` por cada cambio. Corre `python3 -m pytest -q tests`. Si el hook bloquea algo legítimo, no lo debilites para un caso puntual: apruébalo a mano.

## Límites honestos

- El hook revisa el texto del comando con expresiones regulares. Reduce errores de agentes; **no** es un sandbox contra alguien que intenta evadirlo a propósito (por ejemplo, escribiendo un script y ejecutándolo después). Para eso, usa permisos del sistema, contenedores y credenciales con el mínimo acceso.
- Si el hook falla por un error propio, deja pasar el comando y lo registra, para no congelar todas las sesiones. Las pruebas existen para que eso no pase.
- SkillSpector es un análisis estático: detecta riesgos conocidos, no garantiza que algo sea seguro.

## Licencia

MIT. Ver [CREDITS.md](CREDITS.md).

---

## English

Safety and governance for coding agents. An agent profile *asks* the agent not to do something; a hook *prevents* it. This repo ships both, plus templates to get a repository ready for agent work: a tested `PreToolUse` hook that denies irreversible shell commands and asks for approval on risky ones, a skill to vet third-party skills/plugins/MCP servers (SkillSpector scan, pinned commit, lockfile), a skill to choose the lightest agent component, and templates for `CLAUDE.md`, `settings.json`, a skills lockfile, pre-commit and a CI scan.

Install with `/plugin marketplace add nvv-dev/claude-plugins` and `/plugin install agent-guardrails@nvvdev`, or copy the hook into `.claude/hooks/` and register it in `.claude/settings.json` (snippet above). The hook is regex-based: it catches agent mistakes, it is not a sandbox against deliberate evasion. License: MIT.
