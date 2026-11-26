# Worker: PR lifecycle

Read this before you open a PR. The task gives `PR rules: <this file>` and `PR watcher: <path to pr-watch.py>`. You run the PR to the end: CI → review → merge → issue Done. Report each step to the coordinator with your `hc send` command.

## Open the PR

- Branch, PR body and issue link: the task says which. Linear branch names link the PR by themselves; GitHub Issues: `Fixes #N` in the body; other trackers: put the issue link in the body.
- Public repo (the task says): nothing internal in the PR (customer names, internal links, still-open risks). That goes in the tracker comment below.
- Images in the PR body (screenshots): `gh` can't upload them. A claude worker with the browser: open the PR in Chrome, edit the description, attach the file through the upload field, save. No browser (codex): send the image path to the coordinator.
- Issue status: **In Review** (or the tracker's equivalent) once the PR is open.
- **Tracker comment** on the issue (MCP tool or `gh issue comment`): cause found, what changed, behavior change, tests, PR link. The tracker is internal, so it may say more than the PR (e.g. open risks of a security fix), but never secrets or credentials. No tracker tool → send the text to the coordinator; it posts it.

## Watch it: start the watcher, don't poll

```sh
hc run --bg --parent <your name> --name pr-<your name> -- python3 <PR watcher> <pr url>
```

`--parent <your name>` is required (codex strips `HC_TERMINAL_ID`; without it no note reaches you). The watcher polls every 3 min and exits when a check fails, CI finishes, a review / PR comment / thread comment arrives, the head moves, or the PR is merged/closed. Its exit note arrives as your input (`pr-<name> exited … Last lines: …`). Then:

1. `hc rm pr-<your name>`; read what changed (`hc read` it, or `gh pr view`).
2. Act (rules below), report to the coordinator if something needs a decision.
3. Start the watcher again (same command) until the PR is merged or closed. Your own comments and pushes wake it once; ignore those.

`python3 <PR watcher> <pr url> --once` prints the merge checklist: checks, every review with its commit vs head, unresolved threads, merge state, allowed merge methods.

## Merge rule

All must hold. Check with `--once`, not memory:

| Rule | Why |
|---|---|
| Read **every** review, review comment and thread, not `reviewDecision` | A NO-GO can come as a `COMMENTED` review while another reviewer approved |
| No reviewer has an open objection (NO-GO, unanswered question, `[Must fix]`) | Approved ≠ everyone agrees |
| All review threads resolved: answer each, resolve the ones you fixed | Repos may require it; merge is blocked otherwise |
| The approval is on the current head, unless the user waived it | Commits after approval are unreviewed. A base-branch merge commit ("Update branch") pushed by the user is normal and does not count as new code |
| CI green. A failure that looks flaky: rerun once (`gh run rerun <id> --failed`); fails again → report | Don't loop on red CI |
| `[Should fix]` items: report each with your recommendation (fix in this PR vs follow-up issue) and wait | The user decides scope |
| Merge method: one the repo allows (`--once` lists them); squash if allowed, unless the repo's history shows otherwise | |

**Who merges:** by default, report `ready to merge` with the `--once` output and wait for the go. Merge yourself only if the task says so ("merge when green and approved").

## After merge

- Issue → **Done**, unless the coordinator said the issue has more parts.
- Tracker comment: merge commit, follow-ups left (with issue ids), decisions taken in review.
- Report `merged <hash>` and wait. Don't delete the branch or worktree; cleanup comes from the coordinator.

Status mapping (use the tracker's names): start → In Progress (the coordinator does it), PR open → In Review, merged → Done.
