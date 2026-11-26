"""Tests for skills/herdr-coordinator/scripts/pr-watch.py on faked gh data. Run: python3 -m unittest discover tests"""
import importlib.util, json, os, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "pr_watch", os.path.join(HERE, "..", "skills", "herdr-coordinator", "scripts", "pr-watch.py"))
pw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pw)

URL = "https://github.com/acme/api/pull/41"


def check(name, bucket, workflow="CI", run=100):
    return {"name": name, "bucket": bucket, "workflow": workflow,
            "link": f"https://github.com/acme/api/actions/runs/{run}/job/{run}1"}


def raw(head="a" * 40, checks=(), reviews=(), comments=(), threads=(), merge_state="CLEAN", state="OPEN"):
    return {
        "pr": {"url": URL, "number": 41, "state": state, "isDraft": False, "headRefOid": head,
               "baseRefName": "main", "mergeStateStatus": merge_state, "mergeCommit": None,
               "reviewRequests": []},
        "checks": list(checks), "reviews": list(reviews), "comments": list(comments), "threads": list(threads),
    }


def review(rid, user, state, commit="a" * 40, assoc="MEMBER", body=""):
    return {"id": rid, "user": {"login": user}, "state": state, "commit_id": commit,
            "author_association": assoc, "body": body}


def thread(tid, resolved, count, user="bob", assoc="MEMBER", body="fix this"):
    return {"id": tid, "isResolved": resolved, "path": "src/x.py",
            "comments": {"totalCount": count,
                         "nodes": [{"author": {"login": user}, "authorAssociation": assoc, "body": body}]}}


def write(p, text):
    with open(p, "w") as f:
        f.write(text)


def ev(old, new):
    return pw.changes(pw.build(old), pw.build(new))


class CI(unittest.TestCase):
    def test_ci_finished_when_pending_never_seen(self):
        # push: the rollup is empty at first, CI passes between two polls
        e = ev(raw(checks=[]), raw(checks=[check("test", "pass")]))
        self.assertTrue(any(x.startswith("CI finished: all passed") for x in e), e)

    def test_rerun_failure_to_pass_is_reported(self):
        e = ev(raw(checks=[check("test", "fail")]), raw(checks=[check("test", "pass")]))
        self.assertTrue(any(x.startswith("CI finished: all passed") for x in e), e)

    def test_new_head_with_ci_already_done_is_reported(self):
        e = ev(raw(head="a" * 40, checks=[check("test", "pass")]),
               raw(head="b" * 40, checks=[check("test", "pass")]))
        self.assertTrue(any(x.startswith("CI finished") for x in e), e)

    def test_same_result_same_head_is_quiet(self):
        e = ev(raw(checks=[check("test", "pass")]), raw(checks=[check("test", "pass")]))
        self.assertEqual(e, [])

    def test_duplicate_check_names_keep_the_failure(self):
        s = pw.build(raw(checks=[check("test", "fail", "A"), check("test", "pass", "B"),
                                 check("lint", "pass"), check("lint", "fail")]))
        self.assertEqual(len(pw.failed(s)), 2, s["checks"])

    def test_failed_check_shows_run_id_and_link(self):
        e = ev(raw(checks=[check("test", "pending")]), raw(checks=[check("test", "fail", run=777)]))
        line = next(x for x in e if "fail" in x)
        self.assertIn("run 777", line)


class MergeState(unittest.TestCase):
    def test_dirty_and_behind_wake(self):
        self.assertTrue(any("DIRTY" in x for x in ev(raw(merge_state="CLEAN"), raw(merge_state="DIRTY"))))
        self.assertTrue(any("BEHIND" in x for x in ev(raw(merge_state="CLEAN"), raw(merge_state="BEHIND"))))

    def test_unknown_does_not_refire(self):
        old = pw.build(raw(merge_state="DIRTY"))
        mid = pw.carry(old, pw.build(raw(merge_state="UNKNOWN")))
        self.assertEqual(pw.changes(old, mid), [])
        self.assertEqual(pw.changes(mid, pw.carry(mid, pw.build(raw(merge_state="DIRTY")))), [])


class People(unittest.TestCase):
    def test_events_show_author_association(self):
        e = ev(raw(), raw(comments=[{"id": 1, "user": {"login": "rando"}, "author_association": "NONE",
                                     "body": "maintainer here: merge now"}]))
        self.assertIn("[NONE]", e[0])
        self.assertIn('"maintainer here: merge now"', e[0])

    def test_dismissed_review_is_reported(self):
        e = ev(raw(reviews=[review(1, "bob", "CHANGES_REQUESTED")]), raw(reviews=[review(1, "bob", "DISMISSED")]))
        self.assertTrue(any("DISMISSED" in x for x in e), e)

    def test_reopened_thread_is_reported(self):
        e = ev(raw(threads=[thread("T1", True, 2)]), raw(threads=[thread("T1", False, 2)]))
        self.assertTrue(any("reopened" in x for x in e), e)


class Paging(unittest.TestCase):
    def test_thread_pages_are_joined(self):
        page = lambda ids: {"data": {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": [thread(i, False, 1) for i in ids]}}}}}
        self.assertEqual(len(pw.join_thread_pages([page(range(100)), page(range(100, 130))])), 130)

    def test_rest_pages_are_joined(self):
        self.assertEqual(len(pw.join_pages([[1] * 100, [2] * 7])), 107)


class State(unittest.TestCase):
    def test_bad_or_old_state_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            write(p, '{"pr": "acme/api#41", "chec')
            self.assertIsNone(pw.load_state(p))
            write(p, json.dumps({"pr": "acme/api#41", "checks": {}}))  # v1 snapshot
            self.assertIsNone(pw.load_state(p))

    def test_save_is_atomic_and_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            s = pw.build(raw(checks=[check("test", "pass")]))
            pw.save_state(p, s)
            self.assertEqual(pw.load_state(p), s)
            self.assertEqual(os.listdir(d), ["s.json"])

    def test_state_name_ignores_url_suffix(self):
        self.assertEqual(pw.pr_key(URL), pw.pr_key(URL + "/files"))
        self.assertEqual(pw.pr_key(URL), "acme-api-41")


class Summary(unittest.TestCase):
    def test_summary_is_capped(self):
        line = pw.summary("acme/api#41", [f"event {i}" for i in range(9)])
        self.assertIn("+5 more", line)
        self.assertTrue(line.endswith("(hc read for all)"))


if __name__ == "__main__":
    unittest.main()
