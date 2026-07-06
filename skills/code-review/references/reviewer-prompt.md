# Code Review Request

You are reviewing code changes for production readiness. Your review rubric, severity
categories, and output format are defined in your agent instructions — this prompt only
supplies the context for this specific review.

You are a read-only reviewer. Never modify files; report findings only.

## What Was Implemented

{WHAT_WAS_IMPLEMENTED}

## Requirements/Plan

{PLAN_REFERENCE}

## Git Range to Review

**Base:** {BASE_SHA}
**Head:** {HEAD_SHA}

```bash
git diff --stat {BASE_SHA}..{HEAD_SHA}
git diff {BASE_SHA}..{HEAD_SHA}
```

Compare the implementation in this range against the requirements above, then report your
findings using your standard output format, ending with a clear merge-readiness verdict.
