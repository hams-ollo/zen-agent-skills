# Rank 9 evaluation slice

The harness, fixtures and results for the evaluation slice that the
[kit refresh audit](../../docs/reviews/2026-10-kit-refresh-audit.md) ranks ninth. The plan, rubric
and decision rules are in [`PLAN.md`](PLAN.md); the findings are in
[`docs/reviews/2026-10-evaluation-slice.md`](../../docs/reviews/2026-10-evaluation-slice.md).

This lives at the repository root rather than inside a skill directory because `install.py` copies
whole skill directories into an adopter's home, and these fixtures are this kit's own test material.

## Layout

| Path | What it holds |
| --- | --- |
| [`harness/cases.py`](harness/cases.py) | every case, arm, prompt and condition |
| [`harness/conditions.py`](harness/conditions.py) | places rules and skills from pinned revisions |
| [`harness/fixtures.py`](harness/fixtures.py) | builds a fresh scratch repository per run |
| [`harness/run.py`](harness/run.py) | runs the headless child per case, arm, model and repeat |
| [`harness/grade.py`](harness/grade.py) | scores the recorded runs |
| [`harness/selftest.py`](harness/selftest.py) | checks fixtures, conditions and graders without a model |
| `fixtures/` | the fixture trees: `base/` is committed, `ignored/` and `untracked/` are placed after the commit, `change/` is the uncommitted change |
| `results/` | scores, summary and adjudications, once runs exist |

## Running it

Every command needs `EVAL_SCRATCH` set to a directory outside the repository. Runs never write
anywhere else.

```bash
python evals/rank9/harness/selftest.py
```

```bash
python evals/rank9/harness/run.py --part load --model haiku sonnet
```

```bash
python evals/rank9/harness/run.py --part rules --runs 3 --budget-total 200
```

```bash
python evals/rank9/harness/grade.py
```

The child must be able to authenticate on its own: `claude auth status` in a terminal should show a
logged-in account. The harness never reads, copies or passes a credential.
