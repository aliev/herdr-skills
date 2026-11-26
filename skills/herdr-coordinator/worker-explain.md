# Worker: explain the plan for the human

Read this when the task gives `Explain rules: <this file>`. Plans written by agents are hard for a person to decide on. Before you write code, write a short explainer a busy person can read in two minutes, then wait for the decision.

## When

- After you understand the problem and have a plan, **before any code**.
- Again when the approach changes later: update the file and the tracker comment, and report again.

## EXPLAIN.md

At the worktree root, in English (the coordinator retells it to the user). Keep it out of git; if the sandbox blocks that write, skip it: cleanup removes the file.

```sh
grep -qx EXPLAIN.md "$(git rev-parse --git-common-dir)/info/exclude" || echo EXPLAIN.md >> "$(git rev-parse --git-common-dir)/info/exclude"
```

Sections, in this order, each a few short lines:

1. `# <what is wrong, in a user's words>`
2. `## What's broken`: what a user or customer sees, not what the code does.
3. `## Before`: a text sequence diagram of what happens now.
4. `## The fix`: what you will change, by what will happen differently.
5. `## After`: the same diagram with the fix.
6. `## What changes for users`: behavior they will notice; "nothing visible" is a fine answer.
7. `## Still open`: risks, things this fix does not cover.
8. `## Decision needed`: the question the person must answer, with your recommendation.

**Plain language.** Follow the writing rules file the task gives (Simplified Technical English). Also: ordinary words. Explain by what happens, not by the name of a pattern ("the server answers 'already done' instead of charging again", not "idempotent retries"). Short sentences. No terms you made up. Code names only where the reader needs them to find something. If the user has global instructions (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`), read their style rules and follow them; never copy them into the repo.

**Text diagrams** (helix shows text, not Mermaid), each in a ` ```text ` block: fixed width, at most 100 columns, at most 6 participants and 10 messages each. One column per participant, `--->` for a call, `<- - -` for an answer, the label above its arrow:

```text
Customer           App                  Payment server
   |                |                         |
   |  taps Pay      |                         |
   |--------------->|                         |
   |                |  charge card            |
   |                |------------------------>|
   |                |  no answer in time      |
   |                |<- - - - - - - - - - - - |
   |                |  charge card again      |
   |                |------------------------>|
   |                |  ok                     |
   |                |<- - - - - - - - - - - - |
   |                                          |
   [ card charged twice ]
```

Check the diagram width: `awk '/^```text/{f=1;next} /^```/{f=0} f && length > 100' EXPLAIN.md` prints nothing.

## Tracker plan comment

Post the explainer as the plan comment on the issue (MCP tool or `gh issue comment`), with the diagrams as Mermaid `sequenceDiagram` (GitHub and Linear draw it), the same participants and messages as the text version. The public/internal rules in the PR rules file apply: on a public tracker, nothing internal. No tracker tool → skip it; the coordinator has the file.

When you open the PR and the approach changed since the plan, put the updated Mermaid diagrams in the PR body and tracker summary too (public rules apply to the PR).

## Report and wait

```sh
hc send <coordinator> '[<name>] plan ready: <absolute path>/EXPLAIN.md. Decision needed: <one line>'
```

Then wait. No code until the coordinator passes on the decision.
