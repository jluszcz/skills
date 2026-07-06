---
name: code-review
description: >
  Review code changes for correctness, architecture, and production readiness. Trigger whenever
  the user asks to review code — "review my code", "look at what I just wrote", "can you check
  this", "does this look right", "give me a code review" — as well as after completing tasks,
  implementing major features, or before merging. Always trigger after each significant
  implementation step in multi-step workflows so issues are caught before they compound. Also
  trigger when stuck, before a refactor, or after fixing a complex bug.
allowed-tools:
  - Agent
  - Read
  - Bash(git log:*)
  - Bash(git rev-parse:*)
  - Bash(git diff:*)
  - Bash(git show:*)
---

# Code Review

Dispatch code-reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Get git SHAs — run each command separately (no `$()` substitution):**
```bash
git rev-parse origin/main   # → BASE_SHA
git rev-parse HEAD           # → HEAD_SHA
git log --oneline origin/main..HEAD
```

If `origin/main` doesn't exist (repo uses `master`, no remote, or the branch isn't fetched),
substitute the appropriate base branch — or ask the user what to review against.

**2. Dispatch the `code-reviewer` agent:**

Use the Agent tool with `subagent_type: code-reviewer` (namespaced as `jluszcz:code-reviewer`
when installed via the plugin), passing the template below (with placeholders filled in) as the
prompt.

**Placeholders:**
- `{WHAT_WAS_IMPLEMENTED}` - What you just built (a sentence or two)
- `{PLAN_REFERENCE}` - What it should do (plan doc, requirements, task description)
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit

**Agent prompt template:**

Read `references/reviewer-prompt.md` for the full agent prompt template. Fill in the placeholders
(`{WHAT_WAS_IMPLEMENTED}`, `{PLAN_REFERENCE}`, `{BASE_SHA}`, `{HEAD_SHA}`) and use it verbatim as
the prompt passed to the `code-reviewer` subagent. The template only supplies context — the review
rubric and output format live in the agent's own definition, so there is one source of truth.

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

git log --oneline                    # → find the Task 1 commit, grab BASE_SHA from output
git rev-parse HEAD                   # → HEAD_SHA

[Dispatch code-reviewer agent]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index —
    added verifyIndex() and repairIndex() covering 4 issue types
  PLAN_REFERENCE: Task 2 from plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification
