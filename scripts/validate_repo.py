#!/usr/bin/env python3
"""Validate the structure of a skills/agents/plugin repository.

Checks, with no third-party dependencies:
- .claude-plugin/plugin.json (if present) is valid JSON with a kebab-case name;
- .claude-plugin/marketplace.json (if present) has name, owner and plugins;
- every skills/<dir>/SKILL.md has front matter whose name matches the folder,
  a description of at most 1024 characters, and no angle brackets in it;
- every agents/<file>.md has front matter with name (matching the file),
  description and a known model;
- hooks/hooks.json (if present) is valid JSON.

Usage: python3 scripts/validate_repo.py [repo_root]
Exit code 0 when everything passes, 1 otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MODELS = {"sonnet", "opus", "haiku", "inherit"}


def front_matter(path: Path) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def main(root: Path) -> int:
    errors: list[str] = []

    def check_json(rel: str) -> dict | None:
        p = root / rel
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON ({exc})")
            return None

    plugin = check_json(".claude-plugin/plugin.json")
    if plugin is not None and not KEBAB.match(str(plugin.get("name", ""))):
        errors.append(".claude-plugin/plugin.json: 'name' must be kebab-case")

    market = check_json(".claude-plugin/marketplace.json")
    if market is not None:
        for key in ("name", "owner", "plugins"):
            if key not in market:
                errors.append(f".claude-plugin/marketplace.json: missing '{key}'")
        for i, entry in enumerate(market.get("plugins", [])):
            for key in ("name", "source", "description"):
                if key not in entry:
                    errors.append(f"marketplace plugin #{i}: missing '{key}'")

    check_json("hooks/hooks.json")

    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        rel = skill.relative_to(root)
        fm = front_matter(skill)
        if fm is None:
            errors.append(f"{rel}: missing front matter")
            continue
        folder = skill.parent.name
        if fm.get("name") != folder:
            errors.append(f"{rel}: name '{fm.get('name')}' must match folder '{folder}'")
        if not KEBAB.match(folder):
            errors.append(f"{rel}: folder must be kebab-case")
        desc = fm.get("description", "")
        if not desc:
            errors.append(f"{rel}: missing description")
        elif len(desc) > 1024:
            errors.append(f"{rel}: description longer than 1024 characters")
        elif "<" in desc or ">" in desc:
            errors.append(f"{rel}: description must not contain angle brackets")

    for agent in sorted((root / "agents").glob("*.md")):
        rel = agent.relative_to(root)
        fm = front_matter(agent)
        if fm is None:
            errors.append(f"{rel}: missing front matter")
            continue
        if fm.get("name") != agent.stem:
            errors.append(f"{rel}: name must match file name '{agent.stem}'")
        if not fm.get("description"):
            errors.append(f"{rel}: missing description")
        if fm.get("model") and fm["model"] not in MODELS:
            errors.append(f"{rel}: unknown model '{fm['model']}'")

    for err in errors:
        print(f"ERROR {err}")
    print("OK" if not errors else f"{len(errors)} error(s)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()))
