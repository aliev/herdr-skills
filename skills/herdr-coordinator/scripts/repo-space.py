#!/usr/bin/env python3
"""Find the Herdr space that belongs to a repo. Prints its id, or nothing (exit 1).

Usage: python3 repo-space.py <repo main checkout> [repo name]

A space's `folder` is where it was made, not where its terminals are, so match in order:
  1. a space whose folder is the repo's main checkout
  2. a space named after the repo
  3. a space holding a terminal whose cwd is inside the main checkout (not a linked worktree)
"""
import json, os, subprocess, sys


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}


def main():
    repo_main = os.path.realpath(os.path.expanduser(sys.argv[1])).rstrip("/")
    name = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(repo_main)
    spaces = run("herdr-app", "ls").get("spaces", [])
    for s in spaces:
        if s.get("folder") and os.path.realpath(s["folder"]).rstrip("/") == repo_main:
            return print(s["id"])
    for s in spaces:
        if s.get("name") == name:
            return print(s["id"])
    ids = {s["id"] for s in spaces}
    for t in run("hc", "ls", "--json").get("terminals", []):
        cwd = os.path.realpath(t.get("cwd") or "")
        if cwd == repo_main or cwd.startswith(repo_main + "/"):
            space = run("hc", "get", t["address"]).get("labels", {}).get("herdr.space")
            if space in ids:
                return print(space)
    sys.exit(1)


if __name__ == "__main__":
    main()
