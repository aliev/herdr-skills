#!/usr/bin/env python3
"""Create (or reopen) a git worktree and show it in Herdr, like the app's "New worktree…" dialog.

Usage:
  python3 worktree.py <branch> [--from DIR] [--in-tab | --no-open] [--argv JSON] [--task TEXT] [--name NAME] [--no-focus] [--dry-run]

--from     a folder inside the repo (default: this terminal's cwd from `hc get $HC_TERMINAL_ID`, else $PWD)
--in-tab   open the checkout as a tab in the caller's space instead of a new space
--argv     program for the first terminal, e.g. '["claude"]'
--task     first message for that program (needs --argv)
--name     tab name for --in-tab (default: the branch)
--no-open  only create/reuse the checkout; print its path, touch no window

Mirrors ~/.config/herdr-app/mods/worktree/main.js: checkouts go to
<worktrees.directory>/<repo>/<slug(branch)> (settings.json, default ~/.herdr/worktrees);
an existing branch is checked out, a new one starts from HEAD of --from.
The new space is left unnamed so the sidebar nests it under its repo.
Prints one JSON object: {path, branch, created, repo, repo_main, space?, herdr?: <reply>};
`space` is the checkout's space id (new or already open), absent with --no-open/--in-tab.
"""
import argparse, json, os, re, subprocess, sys, unicodedata


def sh(args, cwd=None, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(json.dumps({"error": f"{' '.join(args)}: {(r.stderr or r.stdout).strip()}"}))
    return r


def slug(branch):
    s = unicodedata.normalize("NFC", branch)
    # Same as the mod's [^\p{L}\p{M}\p{N}._-]+ (\w also matches "_", which the mod replaces).
    name = re.sub(r"(?:[^\w.\-]|_)+", "-", s).strip("-")
    if name:
        return name
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return f"branch-{h:08x}"


def worktree_root():
    home = os.environ.get("HERDR_APP_HOME", os.path.expanduser("~/.config/herdr-app"))
    try:
        with open(os.path.join(home, "settings.json")) as f:
            d = json.load(f).get("worktrees", {}).get("directory")
    except (FileNotFoundError, json.JSONDecodeError):
        d = None
    return os.path.expanduser(d or "~/.herdr/worktrees").rstrip("/")


def me():
    tid = os.environ.get("HC_TERMINAL_ID")
    if not tid:
        return {}
    r = sh(["hc", "get", tid], check=False)
    return json.loads(r.stdout) if r.returncode == 0 else {}


def herdr(cmd, payload, dry):
    args = ["herdr-app", "do", cmd, json.dumps(payload)]
    if dry:
        return {"dry_run": args}
    r = sh(args, check=False)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": (r.stderr or r.stdout).strip()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("branch")
    p.add_argument("--from", dest="src")
    p.add_argument("--in-tab", action="store_true")
    p.add_argument("--argv")
    p.add_argument("--task")
    p.add_argument("--name")
    p.add_argument("--no-focus", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-open", action="store_true")
    a = p.parse_args()

    info = me()
    src = a.src or info.get("cwd") or os.getcwd()
    top = sh(["git", "rev-parse", "--show-toplevel"], cwd=src).stdout.strip()
    common = sh(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=src).stdout.strip()
    main_repo = common[:-5] if common.endswith("/.git") else common
    repo = os.path.basename(main_repo)

    # Reuse an existing checkout of this branch wherever it lives.
    path, created = None, False
    cur = {}
    for line in sh(["git", "worktree", "list", "--porcelain"], cwd=main_repo).stdout.splitlines() + [""]:
        if line.startswith("worktree "):
            cur = {"path": line[9:]}
        elif line.startswith("branch "):
            cur["branch"] = line[7:].removeprefix("refs/heads/")
        elif not line and cur:
            if cur.get("branch") == a.branch:
                path = cur["path"]
            cur = {}
    if path is None:
        path = f"{worktree_root()}/{repo}/{slug(a.branch)}"
        exists = sh(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{a.branch}"], cwd=main_repo, check=False).returncode == 0
        add = ["worktree", "add", path, a.branch] if exists else ["worktree", "add", "-b", a.branch, path, "HEAD"]
        if a.dry_run:
            created = {"dry_run": ["git", *add]}
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            sh(["git", *add], cwd=top)
            created = True

    payload: dict = {"folder": path}
    if a.argv:
        payload["argv"] = json.loads(a.argv)
        if a.task:
            payload["task"] = a.task
    if a.no_focus:
        payload["focus"] = False
    out = {"path": path, "branch": a.branch, "created": created, "repo": repo, "repo_main": main_repo}
    if a.no_open:
        print(json.dumps(out, indent=1))
        return

    if a.in_tab:
        space = info.get("labels", {}).get("herdr.space")
        if space:
            payload["space"] = space
        payload["name"] = a.name or a.branch
        out["herdr"] = herdr("tab.new", payload, a.dry_run)
    else:
        # Already shown? select its space instead of making a second one.
        ls = json.loads(sh(["herdr-app", "ls"], check=False).stdout or "{}")
        hit = next((s for s in ls.get("spaces", []) if s.get("folder") == path), None)
        if hit and not a.argv:
            out["space"] = hit["id"]
            out["herdr"] = {"ok": True} if a.no_focus else herdr("space.select", {"id": hit["id"]}, a.dry_run)
        else:
            out["herdr"] = herdr("space.new", payload, a.dry_run)
            if out["herdr"].get("space"):
                out["space"] = out["herdr"]["space"]
    print(json.dumps(out, indent=1))
    if "error" in out["herdr"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
