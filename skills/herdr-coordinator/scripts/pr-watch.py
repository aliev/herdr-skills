#!/usr/bin/env python3
"""Watch a GitHub PR with gh; exit when something needs the agent. Or print its merge checklist.

Usage: python3 pr-watch.py <pr url> [--every 180] [--state FILE]
       python3 pr-watch.py <pr url> --once

Watch mode polls every --every seconds and exits 0 with what changed since the
last saved snapshot: a check failed, CI finished, a new review, PR comment or
review-thread comment, the head moved (a push, e.g. GitHub's "Update branch"),
draft/ready changed, or the PR was merged/closed. The summary is the last line,
so hc's exit note ("Last lines: ...") carries it. Exits 2 after 3 gh errors in a row.

Run it as an hc child of the agent, so its exit note wakes the agent:
  hc run --bg --parent <agent name> --name pr-<agent name> -- python3 pr-watch.py <pr url>

The snapshot is kept in the checkout's git dir (or --state), so a restarted
watcher reports what happened while none was running.
--once prints the merge checklist: checks, every review (with its commit vs the
head), unresolved threads, merge state, the repo's allowed merge methods.
"""
import argparse, json, os, subprocess, sys, time

PENDING = {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED", "EXPECTED"}
FAILED = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "ERROR"}

THREADS = """query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
reviewThreads(first:100){nodes{id isResolved path comments(last:1){totalCount nodes{author{login} body}}}}}}}"""


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"gh {args[0]} failed")
    return json.loads(r.stdout)


def first_line(text, n=90):
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    return line[:n] + ("…" if len(line) > n else "")


def check_state(c):
    if c.get("__typename") == "StatusContext":
        return c.get("state") or "PENDING"
    if c.get("status") != "COMPLETED":
        return "PENDING"
    return c.get("conclusion") or "NEUTRAL"


def snapshot(url):
    pr = gh("pr", "view", url, "--json",
            "url,number,state,isDraft,headRefOid,mergeStateStatus,mergeCommit,"
            "statusCheckRollup,reviews,comments")
    owner, repo = pr["url"].split("/")[3:5]
    threads = gh("api", "graphql", "-f", f"query={THREADS}", "-F", f"o={owner}", "-F", f"r={repo}",
                 "-F", f"n={pr['number']}")["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return {
        "pr": f"{owner}/{repo}#{pr['number']}",
        "repo": f"{owner}/{repo}",
        "state": pr["state"],
        "draft": pr["isDraft"],
        "head": pr["headRefOid"],
        "merge_state": pr.get("mergeStateStatus"),
        "merge_commit": (pr.get("mergeCommit") or {}).get("oid"),
        "checks": {(c.get("name") or c.get("context")): check_state(c) for c in pr.get("statusCheckRollup") or []},
        "reviews": {r["id"]: {"author": (r.get("author") or {}).get("login"), "state": r["state"],
                              "commit": (r.get("commit") or {}).get("oid"), "body": first_line(r.get("body"))}
                    for r in pr.get("reviews") or []},
        "comments": {c["id"]: {"author": (c.get("author") or {}).get("login"), "body": first_line(c.get("body"))}
                     for c in pr.get("comments") or []},
        "threads": {t["id"]: {"resolved": t["isResolved"], "path": t.get("path"),
                              "count": t["comments"]["totalCount"],
                              "author": ((t["comments"]["nodes"] or [{}])[0].get("author") or {}).get("login"),
                              "body": first_line((t["comments"]["nodes"] or [{}])[0].get("body"))}
                    for t in threads},
    }


def changes(old, new):
    ev = []
    if new["state"] != old["state"]:
        ev.append(f"PR {new['state'].lower()}" + (f" as {new['merge_commit'][:9]}" if new["merge_commit"] else ""))
    if new["head"] != old["head"]:
        ev.append(f"head moved {old['head'][:7]} -> {new['head'][:7]} (a push; check whether it was a base merge)")
    if new["draft"] != old["draft"]:
        ev.append("marked draft" if new["draft"] else "marked ready for review")
    for rid, r in new["reviews"].items():
        if rid not in old["reviews"]:
            on = "on head" if r["commit"] == new["head"] else f"on {(r['commit'] or '?')[:7]}, not head"
            ev.append(f"review {r['state']} by {r['author']} {on}: {r['body'] or '(no body)'}")
    for cid, c in new["comments"].items():
        if cid not in old["comments"]:
            ev.append(f"comment by {c['author']}: {c['body']}")
    for tid, t in new["threads"].items():
        o = old["threads"].get(tid)
        if o is None or t["count"] > o["count"]:
            ev.append(f"thread comment by {t['author']} on {t['path']}: {t['body']}")
    newly_failed = [n for n, s in new["checks"].items() if s in FAILED and old["checks"].get(n) not in FAILED]
    if newly_failed:
        ev.append("check failed: " + ", ".join(sorted(newly_failed)))
    was_pending = any(s in PENDING for s in old["checks"].values())
    now_pending = any(s in PENDING for s in new["checks"].values())
    if was_pending and not now_pending and new["checks"]:
        failed = sorted(n for n, s in new["checks"].items() if s in FAILED)
        ev.append("CI finished: " + ("failed " + ", ".join(failed) if failed else "all passed"))
    return ev


def checklist(s):
    methods = gh("repo", "view", s["repo"], "--json", "squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed")
    allowed = [m for m, k in (("squash", "squashMergeAllowed"), ("merge", "mergeCommitAllowed"),
                              ("rebase", "rebaseMergeAllowed")) if methods.get(k)]
    states = list(s["checks"].values())
    failed = sorted(n for n, st in s["checks"].items() if st in FAILED)
    open_threads = [t for t in s["threads"].values() if not t["resolved"]]
    out = [f"PR {s['pr']} {s['state']}{' DRAFT' if s['draft'] else ''} head {s['head'][:7]}"
           + (f" merged as {s['merge_commit'][:9]}" if s["merge_commit"] else ""),
           f"merge state: {s['merge_state']}  allowed methods: {', '.join(allowed)}",
           f"checks: {sum(x not in PENDING and x not in FAILED for x in states)} ok, "
           f"{sum(x in PENDING for x in states)} pending, {len(failed)} failed {' '.join(failed)}".rstrip(),
           f"reviews ({len(s['reviews'])}, read every one; reviewDecision is not enough):"]
    for r in s["reviews"].values():
        on = "head" if r["commit"] == s["head"] else (r["commit"] or "?")[:7]
        out.append(f"  {r['state']:<17} {r['author']} on {on}: {r['body'] or '(no body)'}")
    out.append(f"threads: {len(s['threads'])}, unresolved {len(open_threads)}")
    for t in open_threads:
        out.append(f"  {t['path']}: {t['author']}: {t['body']}")
    out.append(f"PR comments: {len(s['comments'])}")
    return "\n".join(out)


def default_state(url):
    r = subprocess.run(["git", "rev-parse", "--absolute-git-dir"], capture_output=True, text=True)
    base = r.stdout.strip() if r.returncode == 0 else os.path.expanduser("~/.cache")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "pr-watch-" + "-".join(url.rstrip("/").split("/")[-4:]) + ".json")


def main():
    p = argparse.ArgumentParser(description="Watch a GitHub PR; exit when something needs the agent.")
    p.add_argument("pr", help="PR url (or number inside the repo's checkout)")
    p.add_argument("--every", type=int, default=180, help="seconds between polls (default 180)")
    p.add_argument("--once", action="store_true", help="print the merge checklist and exit")
    p.add_argument("--state", help="snapshot file (default: in the checkout's git dir)")
    a = p.parse_args()

    if a.once:
        print(checklist(snapshot(a.pr)))
        return
    state_file = a.state or default_state(a.pr)
    old = None
    if os.path.exists(state_file):
        with open(state_file) as f:
            old = json.load(f)
    errors = 0
    while True:
        try:
            new = snapshot(a.pr)
            errors = 0
        except Exception as e:  # network blips, machine sleep, gh auth expiry
            errors += 1
            print(f"gh error {errors}/3: {e}", flush=True)
            if errors >= 3:
                print(f"PR watch stopped: gh failed 3 times in a row ({a.pr})")
                sys.exit(2)
            time.sleep(a.every)
            continue
        ev = changes(old, new) if old else []
        with open(state_file, "w") as f:
            json.dump(new, f)
        if ev:
            for e in ev:
                print(e)
            print(f"PR {new['pr']}: " + "; ".join(e if len(e) <= 70 else e[:69] + "…" for e in ev))
            return
        if new["state"] != "OPEN":
            print(f"PR {new['pr']} is {new['state'].lower()}; nothing to watch")
            return
        old = new
        time.sleep(a.every)


if __name__ == "__main__":
    main()
