# Fix: "refusing to merge unrelated histories"

This happens when your local branch and `origin/main` have no common commit (e.g. local was inited with one commit, remote has a different history).

## Option A: Merge and keep both histories (recommended if you want to keep local work)

From project root:

```bash
git pull origin main --allow-unrelated-histories
```

- Git will create a merge commit joining both histories.
- You may get **merge conflicts**; fix them, then:
  ```bash
  git add .
  git commit -m "Merge origin/main with local (resolve conflicts)"
  ```

## Option B: Make local match GitHub exactly (discard local commit(s))

**Warning:** This overwrites your local branch with `origin/main`. Any local-only commits are lost.

```bash
git fetch origin
git checkout main
git reset --hard origin/main
```

(If you're on `master`, use `git checkout -b main origin/main` then optionally delete or rename `master`.)

## Option C: Keep local as-is, use GitHub code in a branch

```bash
git fetch origin
git branch main origin/main
git checkout main
```

Now you have `main` = GitHub state, and your previous branch (e.g. `master`) still has your local commit.
