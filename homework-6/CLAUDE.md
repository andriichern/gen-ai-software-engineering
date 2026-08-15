# Coverage Check Before Push

Before pushing (via `gh push` or `git push`), run:

```bash
bash scripts/check-coverage.sh
```

If coverage is below 80%, do not proceed with the push.
