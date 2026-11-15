#!/usr/bin/env python3
"""List live coordinator workers (terminals labelled coord.task), one JSON object per line.

Usage: python3 workers.py [--by <coordinator address>] [--cwd <path>] [--orphans]

  --by       only workers whose coord.by is this address (your own workers)
  --cwd      only workers whose cwd is this folder or inside it (is a worktree taken?)
  --orphans  only workers whose coordinator is gone: coord.by is not a live terminal
             running an agent (it exited, or its terminal was closed)

`hc ls --label` needs key=value and `hc ls` doesn't print labels, so this reads
every live terminal with `hc get`.
"""
import argparse, json, os, subprocess


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--by")
    p.add_argument("--cwd")
    p.add_argument("--orphans", action="store_true")
    a = p.parse_args()
    live = run("hc", "ls", "--json").get("terminals", [])
    # An agent session has a status (working/blocked/done/idle); a bare shell doesn't.
    agents = {t["address"] for t in live if t.get("status")}
    want = os.path.realpath(os.path.expanduser(a.cwd)).rstrip("/") if a.cwd else None
    for t in live:
        labels = run("hc", "get", t["address"]).get("labels", {})
        if "coord.task" not in labels:
            continue
        by = labels.get("coord.by")
        cwd = os.path.realpath(t.get("cwd") or "")
        if a.by and by != a.by:
            continue
        if want and not (cwd == want or cwd.startswith(want + "/")):
            continue
        if a.orphans and by in agents:
            continue
        print(json.dumps({
            "address": t["address"], "name": t.get("name"), "status": t.get("status"), "cwd": cwd,
            "repo": labels.get("coord.repo"), "task": labels.get("coord.task"), "by": by,
            "owner_alive": by in agents,
        }))


if __name__ == "__main__":
    main()
