## Summary

<!-- One or two sentences: what this changes, and why. -->

## How this was verified

<!-- Check what you ran. All four are standard-library only, so there is nothing to install. -->

- [ ] `python scripts/validate-skills.py`
- [ ] `python -m unittest discover -s tests -p "test_*.py"`
- [ ] `python .tasks/validate.py --strict`
- [ ] `python scripts/build-adapters.py --dry-run`

For anything a command cannot prove, say what you did and what you saw. If this adds or changes a
skill, that means naming the real work you ran it on: no skill ships cold, and no command can
demonstrate otherwise.

## Closing a linked issue

Skip this section if it does not close one. Otherwise put the reference in **this description**, not
the title:

```
Closes #123
```

Three rules, each of which fails silently when broken: repeat the keyword for every issue
(`Closes #1, #2` closes only `#1`), target the default branch or the keyword is inert, and check the
form is one GitHub recognises. Why each one matters, and what to check when an issue does not close,
is in [docs/ISSUE-LINKING.md](https://github.com/hams-ollo/zen-agent-skills/blob/main/docs/ISSUE-LINKING.md).
