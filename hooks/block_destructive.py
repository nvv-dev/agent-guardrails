#!/usr/bin/env python3
"""PreToolUse hook for Claude Code: blocks or escalates destructive shell commands.

Reads the hook payload from stdin. For Bash tool calls it checks the command
against two rule sets:

- DENY: never allowed from an agent. A human runs it by hand if truly needed.
- ASK:  allowed only after the human approves that specific call.

Anything else passes through untouched. The hook never fails closed on its own
bugs: an unexpected payload is let through and logged to stderr, so a broken
hook cannot freeze every session. The test suite in tests/ guards the rules.

To adapt the rules, edit DENY_RULES / ASK_RULES and add a test case for every
change. Never weaken a rule to unblock a single command: approve it instead.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    reason: str


def _r(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE)


# Targets that make a recursive delete catastrophic.
_DANGEROUS_RM_TARGET = r"""(?:/|/\*|~|~/|~/\*|\$HOME/?\*?|\.|\./|\.\.|\.\./?|\*|/(?:etc|usr|var|home|Users|opt|bin|boot|lib|root)/?)"""
_RM_RECURSIVE_FORCE = (
    r"\brm\s+(?:-[a-z]*r[a-z]*f[a-z]*|-[a-z]*f[a-z]*r[a-z]*|(?:-[a-z]+\s+)*-r\s+(?:-[a-z]+\s+)*-f"
    r"|(?:-[a-z]+\s+)*-f\s+(?:-[a-z]+\s+)*-r|--recursive\s+--force|--force\s+--recursive)\b"
)

DENY_RULES: tuple[Rule, ...] = (
    Rule("rm-root", _r(_RM_RECURSIVE_FORCE + r"(?:\s+-\S+)*\s+[\"']?" + _DANGEROUS_RM_TARGET + r"[\"']?(?:\s|;|&|\||$)"),
         "Recursive delete of the root, home, current directory or a wildcard."),
    Rule("git-force-push", _r(r"\bgit\s+push\b(?=[^\n;&|]*(?:\s--force(?!-with-lease)\b|\s-f\b|\s\+\S+))"),
         "Force push rewrites remote history. Use --force-with-lease and ask for approval."),
    Rule("no-verify", _r(r"\bgit\s+(?:commit|push|merge|rebase)\b[^\n;&|]*\s--no-verify\b"),
         "Skipping git hooks (secret scanning, linters) is not allowed."),
    Rule("sql-drop", _r(r"\b(?:DROP\s+(?:DATABASE|SCHEMA|TABLE|ROLE|USER)|TRUNCATE\s+(?:TABLE\s+)?\w)"),
         "SQL DROP or TRUNCATE: run it by hand through a reviewed migration, never from an agent."),
    Rule("kubectl-mass-delete", _r(r"\bkubectl\b[^\n;&|]*\bdelete\b[^\n;&|]*(?:\b(?:namespace|namespaces|ns|pv|pvc|node|nodes|crd|crds)\b|--all\b|\s-A\b|--all-namespaces\b)"),
         "Mass delete in Kubernetes (namespaces, volumes, nodes or --all)."),
    Rule("iac-destroy", _r(r"\b(?:terraform|tofu)\s+(?:destroy\b|apply\b[^\n;&|]*-destroy\b)"),
         "Destroying infrastructure with Terraform/OpenTofu."),
    Rule("iac-auto-approve", _r(r"\b(?:terraform|tofu)\s+apply\b[^\n;&|]*-auto-approve\b"),
         "apply with -auto-approve skips the plan review."),
    Rule("disk-wipe", _r(r"\bmkfs(?:\.\w+)?\b|\bdd\b[^\n;&|]*\bof=/dev/|>\s*/dev/(?:sd|nvme|disk|vd)|\bdiskutil\s+(?:erase|zero|secureErase)"),
         "Formatting or overwriting disks."),
    Rule("power", _r(r"(?:^|[;&|]\s*|\bsudo\s+)(?:shutdown|reboot|halt|poweroff)\b|\bsystemctl\s+(?:reboot|poweroff|halt)\b"),
         "Shutting down or rebooting the machine."),
    Rule("fork-bomb", _r(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "Fork bomb."),
    Rule("chmod-777", _r(r"\bchmod\s+(?:-R\s+)?(?:0?777|a\+rwx)\b"), "777 permissions open files to every user."),
    Rule("pipe-to-shell", _r(r"\b(?:curl|wget)\b[^\n;&]*\|\s*(?:sudo\s+)?(?:ba|z|da)?sh\b"),
         "Downloading and running a script unseen. Download it, read it, then run it separately."),
    Rule("read-dotenv", _r(r"\b(?:cat|less|more|head|tail|bat|grep|awk|sed)\b[^\n;&|]*(?:^|[\s/])\.env(?!\.(?:example|sample|template)\b)(?:\.[\w-]+)?\b"),
         "Reading a .env file puts secrets into the model's context."),
    Rule("gh-repo-delete", _r(r"\bgh\s+repo\s+delete\b"), "Deleting a GitHub repository."),
    Rule("crontab-wipe", _r(r"\bcrontab\s+-r\b"), "Deleting the whole crontab."),
)

ASK_RULES: tuple[Rule, ...] = (
    Rule("rm-recursive", _r(_RM_RECURSIVE_FORCE), "Forced recursive delete."),
    Rule("git-reset-hard", _r(r"\bgit\s+reset\s+[^\n;&|]*--hard\b"), "git reset --hard discards local changes."),
    Rule("git-clean", _r(r"\bgit\s+clean\s+[^\n;&|]*-[a-z]*f"), "git clean deletes untracked files."),
    Rule("git-discard", _r(r"\bgit\s+(?:checkout\s+--\s+\.|restore\s+(?:--\S+\s+)*\.(?:\s|$))"), "Discards working tree changes."),
    Rule("git-branch-delete", _r(r"\bgit\s+branch\s+[^\n;&|]*-D\b"), "Deletes a branch without checking it was merged."),
    Rule("git-push-main", _r(r"\bgit\s+push\b[^\n;&|]*\b(?:main|master)\b"), "Direct push to the main branch."),
    Rule("git-push-lease", _r(r"\bgit\s+push\b[^\n;&|]*--force-with-lease\b"), "Force push with lease."),
    Rule("git-history-rewrite", _r(r"\bgit\s+(?:filter-branch|filter-repo)\b"), "History rewrite."),
    Rule("sql-delete-no-where", _r(r"\bDELETE\s+FROM\s+[\w.\"]+\s*(?:;|$|[\"'])"), "DELETE without WHERE."),
    Rule("kubectl-delete", _r(r"\bkubectl\b[^\n;&|]*\bdelete\b"), "Deleting Kubernetes resources."),
    Rule("helm-uninstall", _r(r"\bhelm\s+(?:uninstall|delete)\b"), "Uninstalling a Helm release."),
    Rule("iac-apply", _r(r"\b(?:terraform|tofu)\s+apply\b"), "Applying infrastructure changes."),
    Rule("ansible-run", _r(r"\bansible-playbook\b(?![^\n;&|]*--(?:check|syntax-check|list-tasks|list-hosts)\b)"),
         "Running a playbook against real servers; run it with --check first."),
    Rule("sudo", _r(r"(?:^|[;&|]\s*)sudo\b"), "Command with administrator privileges."),
    Rule("sops-decrypt", _r(r"\bsops\s+(?:-d\b|--decrypt\b|decrypt\b)"), "Decrypting secrets puts them into the context."),
    Rule("docker-prune", _r(r"\bdocker\s+(?:system\s+prune|volume\s+(?:rm|prune)|image\s+prune\s+-a)"), "Docker cleanup that deletes data."),
    Rule("gh-secret", _r(r"\bgh\s+(?:secret|variable)\s+(?:set|delete)\b"), "Changing GitHub secrets or variables."),
)


def evaluate(command: str) -> tuple[str, Rule] | None:
    """Return ("deny"|"ask", rule) for the first matching rule, or None."""
    for rule in DENY_RULES:
        if rule.pattern.search(command):
            return "deny", rule
    for rule in ASK_RULES:
        if rule.pattern.search(command):
            return "ask", rule
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:  # never block every session on a bad payload
        print(f"block_destructive: invalid payload, letting it through ({exc})", file=sys.stderr)
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    verdict = evaluate(command)
    if verdict is None:
        return 0

    decision, rule = verdict
    prefix = "Blocked" if decision == "deny" else "Needs approval"
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"{prefix} [{rule.name}]: {rule.reason}",
        }
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
