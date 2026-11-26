# herdr-skills

Agent skills for the [Herdr](https://herdr.dev) desktop app (`herdr-app`) and [herdr-core](https://github.com/herdrdev/herdr-core) (`hc`). Works with Claude Code and Codex.

| Skill | What it does |
|---|---|
| `herdr-app` | Drive the Herdr window from an agent: spaces, tabs, panes, themes, layouts, mods, screenshots, and git worktrees opened as spaces. Routes "run/read/wait on agents" to `hc`. |
| `herdr-coordinator` | One chat you always talk to. "Let's work on repo X" → finds or creates the repo's space. "Task: …" → worktree + a claude/codex worker in it, task delivered, results and questions relayed back to you. Can read and message any Herdr session. |

Not for the older terminal multiplexer `herdr` (Herdr TUI) — it has its own server and CLI.

## Requirements

- Herdr desktop app and herdr-core (`herdr-app`, `hc` on `PATH`) — `curl -fsSL https://releases.herdr.dev/app/install.sh | sh`
- `git`, `python3`, `jq`
- Workers: `claude` and/or `codex`

## Install

**Any agent (Claude Code, Codex, …)** via the [skills CLI](https://github.com/vercel-labs/skills):

```sh
npx skills add aliev/herdr-skills -g
```

**Claude Code plugin:**

```text
/plugin marketplace add aliev/herdr-skills
/plugin install herdr@herdr-skills
```

Install both skills together: the coordinator uses `herdr-app`'s worktree script from the sibling folder. On first use the coordinator copies its worker templates into `~/.config/herdr-core/templates/` (`worker-claude`, `worker-codex`); to do it by hand: `sh skills/herdr-coordinator/scripts/install-templates.sh`.

## Use

Open a terminal in Herdr, start `claude` and run `/herdr-coordinator` (Codex: ask it to use the herdr-coordinator skill). Then talk to it in any language:

```text
let's work on requests
task: add retries to the HTTP client
same repo, via codex: update the README
what's going on in go-sqlite3?
```

Workers run as `hc` children in a tab of their worktree's space (nested under the repo's space), survive a coordinator restart (`--outlive-parent`), and report back with `hc send <coordinator> '[<name>] …'`. A task can be an issue link (Linear, GitHub Issues, Jira, …). A worker that opens a PR runs it to the end (CI → review → merge → issue Done), woken by `scripts/pr-watch.py` instead of polling; it merges only on your go. Claude workers start with `claude --chrome` (Claude in Chrome), e.g. to put screenshots in a PR body. The full cycle, with a sequence diagram: [docs/how-it-works.md](docs/how-it-works.md).

### Codex notes

- Codex strips `HC_TERMINAL_ID` from its shell, so the coordinator writes its own address into each task.
- Codex workers start with `--sandbox workspace-write -c sandbox_workspace_write.network_access=true --add-dir ~/.local/state/herdr-core`; without network access its sandbox can't reach the core socket. This gives codex workers network access.
- Codex as the coordinator needs the same flags plus `--add-dir ~/.config/herdr-app`.

## Layout

```text
skills/herdr-app/            SKILL.md, scripts/worktree.py
skills/herdr-coordinator/    SKILL.md, worker-pr.md (worker PR rules), templates/worker-*.md,
                             scripts/repo-space.py, workers.py, pr-watch.py, install-templates.sh
.claude-plugin/              plugin.json, marketplace.json
docs/how-it-works.md         idea + sequence diagram of the coordinator/worker cycle
```

## License

MIT
