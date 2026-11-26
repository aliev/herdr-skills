# Writing rules (Simplified Technical English)

Agents misuse words. So all text an agent writes follows ASD-STE100 Simplified Technical English: `EXPLAIN.md`, tracker plan and summary comments, PR bodies, commit messages, worker reports (`[<name>] …`), and the coordinator's instructions to workers.

If the `asd-ste100` skill is available (Claude Code), use it. Otherwise (codex) follow this summary:

| Rule | Bad | Good |
|---|---|---|
| One word = one meaning | "run" for start, execute and a CI run | "start" the watcher, "run" the tests, "CI run" only for CI |
| One name per thing; never switch names. Source text uses several names for one thing → pick one (the name in the code, if any) and use only it. Not sure two names mean one thing → ask | lease / claim / lock for the same thing | "lock" every time |
| Instructions: max 20 words. Descriptions: max 25 words per sentence | | Split long sentences |
| Active voice | "The PR was merged by the worker" | "The worker merged the PR" |
| One action per instruction | "Fetch, rebase and push" | "Fetch origin." "Rebase on origin/main." "Push the branch." |
| No noun chains (max 3 nouns) | "PR review thread resolution status check" | "the check that all review threads are resolved" |
| No phrasal verbs or idioms | "set up", "figure out", "kick off", "on the fly" | "make", "find", "start", "during the run" |
| Keep code names, paths and commands verbatim | "the watch script" | `pr-watch.py` |

Before you send or commit text, check it: count the words in each long sentence, and check that each thing has the same name everywhere.

STE controls how agents write in English. It does not change the language boundary: the coordinator still talks to the user in the user's language.
