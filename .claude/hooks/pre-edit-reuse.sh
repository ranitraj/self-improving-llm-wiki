#!/usr/bin/env bash
# PreToolUse hook for Edit|Write|MultiEdit.
# Nudges Claude to prefer reuse and consistency over rewriting.
# See https://docs.claude.com/en/docs/claude-code/hooks
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"Before writing new code: (a) grep for an existing utility that already does this — reuse beats rewrite. (b) Match parameter names/order of nearby similar functions for consistency. (c) If logic already exists elsewhere, refactor the existing one instead of duplicating."}}
JSON
