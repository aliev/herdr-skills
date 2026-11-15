---
name: herdr-app
description: Use when the user mentions Herdr, herdr-app, herdr-core or `hc`, or asks to open, create, switch, rename, split, zoom or close spaces, tabs, panes or terminals, start an agent in a new space/tab, make a git worktree "in herdr", change Herdr themes, layouts, keys, settings or mods, or screenshot the Herdr window. Also when $HC_TERMINAL_ID is set and the request is about the window around this session.
---

# Herdr app + herdr-core

Two programs, one system:
- **`herdr-app`** — the desktop window: spaces › tabs › panes, layouts, mods, themes. Changes what the person *sees*.
- **`hc`** (= `herdr-core`) — runs every terminal; they survive the window closing. Starts, reads, messages, waits on programs and agents.

**Not this skill:** the old terminal multiplexer `herdr` (Herdr TUI: `herdr pane split`, `herdr workspace …`, `HERDR_ENV=1`, `HERDR_PANE_ID`, `~/.config/herdr/`). It has its own server and shares nothing with the app. Never use the `herdr` binary here. If `HC_TERMINAL_ID` is unset but `HERDR_ENV=1` is, you are inside the TUI — tell the user this skill doesn't apply.

**Coordinator role** (one chat that dispatches tasks to workers in worktrees and relays): use the `herdr-coordinator` skill on top of this one.

## Step 0 — load the live manuals (every session, once)

Both binaries print their own up-to-date guide; they change weekly, so read them instead of trusting memory:

```sh
herdr-app --skill        # window control, layouts/mods rules
hc --skill               # agents: run/send/wait/read/cleanup, templates, machines
herdr-app commands       # every `do` command with args (JSON)
```

For layouts/keys/settings/mods, also read `~/.config/herdr-app/AGENTS.md` (and `herdr.d.ts` beside it) before editing.

## Step 1 — locate yourself (focus ≠ you)

The person may be looking at another tab. Commands without a target act on the **focused** space/pane/folder, not yours. Resolve your own IDs first and pass them explicitly:

```sh
hc get "$HC_TERMINAL_ID" | jq '{cwd: .foreground.cwd // .cwd, space: .labels["herdr.space"], tab: .labels["herdr.tab"]}'
herdr-app ls | jq --arg t "$HC_TERMINAL_ID" '.spaces[] | .tabs[] | .terminals[] | select(.terminal==$t) | .pane'
herdr-app status         # what is shown/focused right now + file/mod errors
```

Naming: give every new space/tab an explicit useful name — except worktree spaces (see below).

IDs: spaces `sp…`, tabs `tb…`, panes `p…`, terminals `t7` / `machine/t7`. Take them from `ls`; never guess.

## Quick reference

`herdr-app do <cmd> --key value …` or `herdr-app do <cmd> '<one JSON object>'`. Arrays/objects as JSON (`--argv '["claude"]'`). Replies `{…ids…}` or `{"error":…}` with exit 1 — read it, then confirm with `ls`/`status`.

| Want | Command |
|---|---|
| New space for a folder, with agent | `do space.new --name api --folder ~/code/api --argv '["claude"]' --task "…"` |
| …without stealing the person's view | add `--focus false` |
| Space on SSH machine | `do space.new --machine vps --folder /srv/api` (`hc machine ls`) |
| Tab in *my* space | `do tab.new --space <my space> --name "fix login" --folder <dir> --argv '["claude"]' --task "…"` |
| Split a pane | `do pane.split --direction right\|down --pane <pane> --argv '["npm","test"]'` → reply `{"pane","terminal"}` is the new pane; use it for zoom/focus |
| Zoom (toggle — twice unzooms) / focus / swap | `do pane.zoom --pane P`, `do pane.focus --pane P`, `do pane.swap '{"pane":P,"target":Q}'` |
| Go to space / tab | `do space.select --id S`, `do tab.select --id T` |
| Rename | `do space.rename --id S --name x`, `do tab.rename --id T --name x` |
| Close (destructive: ends its terminals) | `do tab.close --id T --confirmed true`, `do space.close --id S --confirmed true` — only when asked |
| Show a background hc agent in a pane | `do terminal.keep --terminal t9 --place right`; hide again: `do terminal.park --terminal t9` |
| Jump to an agent | `do agent.focus --terminal t7` |
| Theme / layout | `do app.theme --name graphite` (dark presets: `graphite` `ink` `moss`; light: `paper`; or a `themes/<name>` file). It sets only that lightness half — to force dark regardless of the OS set `"appearance": "dark"` in `settings.json`. `do layout.switch --name terminals` |
| Settings UI / palette | `do app.settings`, `do app.palette` |
| See the window | `herdr-app shot /tmp/h.png` then view the image |

Anything not listed: `herdr-app commands | jq '.[] | select(.name|test("tab"))'`.

## Git worktree in a space

`<skill dir>` is the folder containing this SKILL.md. Herdr's own "New worktree…" dialog checks out to `<worktrees.directory>/<repo>/<branch-slug>` (`settings.json`, default `~/.herdr/worktrees`) and opens it as a **new unnamed space**, which the sidebar nests under the repo's space. Do the same non-interactively with the bundled script (finds the repo from your terminal's cwd; reuses an existing checkout of the branch):

```sh
python3 <skill dir>/scripts/worktree.py feat/login --argv '["claude"]' --task "Implement login"
python3 <skill dir>/scripts/worktree.py feat/login --in-tab       # tab in MY space instead
python3 <skill dir>/scripts/worktree.py feat/login --from ~/code/app --no-focus --dry-run
```

Prints `{path, branch, created, herdr}`. New branches start from the source checkout's HEAD; existing branches are checked out. Do not name the space (`--name`) — naming breaks nesting under the repo. Not in a git repo → the script errors; tell the user.

Remove a worktree only when asked: close its space first (`space.close --confirmed true`), then `git -C <main repo> worktree remove <path>`; check `git status` there first and never `--force` uncommitted work without consent.

## Window vs core: which tool

| Goal | Use |
|---|---|
| Person should **see** it (space/tab/split) | `herdr-app do …` |
| Background worker / orchestration, read its output, wait for it, message it | `hc run --bg --name …`, `hc read`, `hc wait`, `hc send` (see `hc --skill`) |
| Background agent + "tell me when done" | `hc run --bg --name rev --cwd <dir> claude "<exact scope>. Report with hc send $HC_TERMINAL_ID when done."` then `hc wait rev`; afterwards `hc read rev --lines 100`. Ask the user for the scope if they gave none |
| Background worker that should appear in a space later | `hc` with label `herdr.space=<id>` (+ `herdr.tab=<id>`), or `terminal.keep` |

## Customizing (themes, keys, layouts, mods)

Edit files in `~/.config/herdr-app` (`settings.json`, `keys.json`, `layouts/`, `mods/`, `themes/`) — saves hot-reload. Shipped layouts/mods: `do layout.clone` / `do mod.clone` first, edit the copy. After every edit: `herdr-app status` (errors / `<name>.error` files), for mods `herdr-app check mods/<name>`, then `herdr-app shot` and look. A still-working window is not proof the edit applied.

## Common mistakes

| Mistake | Fix |
|---|---|
| Using `herdr pane split` / `herdr workspace create` | That is the TUI. Use `herdr-app do …` |
| `tab.new`/`pane.split` without `--space`/`--pane` | Lands where the person is looking, not where you are. Pass IDs from Step 1 |
| Running bare `herdr-app` to inspect | Opens/raises the window. Use `ls`/`status` |
| `--task` with no `--argv` | Task is the first message to the program in argv |
| Creating spaces/tabs the person didn't ask for | Each one is shown immediately; use `hc run --bg` for invisible work |
| `--argv '["npm","test"]'` and expecting the pane to stay | Pane ends with the program. Keep a shell: `--argv '["<sh>","-c","npm test; exec <sh>"]'` where `<sh>` = `hc get "$HC_TERMINAL_ID" \| jq -r '.argv[0]'` (the tool's own `$SHELL` may differ from the user's) |
| Treating a `do` success as "the program works" | It means the terminal started. Check with `hc read <t>` |
| Stopping/restarting the app or core | Never. Not yours |
