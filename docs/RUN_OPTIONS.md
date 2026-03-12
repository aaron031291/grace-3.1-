# Run options: GitHub vs Grace native

GRACE supports two ways to run and operate the system. You can use either path today and swap to the other later.

| Concern | GitHub path | Grace native path |
|--------|-------------|-------------------|
| **Run backend/frontend** | Same scripts | `start_grace.bat` (Windows) / `start_grace.sh` (Unix) |
| **CI (lint/test/build)** | `.github/workflows/ci.yml` (GitHub Actions) | Genesis `grace-ci` via `POST /api/cicd/trigger` |
| **CD / deploy** | `.github/workflows/cd.yml` (e.g. ghcr.io) | Genesis `grace-deploy` (local/Docker) |
| **Repo cloning / knowledge base** | GitHub connector (optional) | Local `git clone` + file-based ingestion |

## Grace native in short

- **No GitHub account or token** required to run the app or CI.
- **Start:** `start_grace.bat` or `start_grace.sh`.
- **CI/CD:** Use Genesis pipelines (`grace-ci`, `grace-quick`, `grace-deploy`). See [Genesis CI/CD Pipelines](../knowledge_base/cicd_pipelines/README.md).

## When to use which

- **GitHub path:** Use when you already use GitHub for repos, Actions, and (optionally) the GitHub connector for the knowledge base.
- **Grace native path:** Use when you want to run and run CI entirely without GitHub, or when you plan to switch away from GitHub later.

Both options are supported; choose one or the other, or run one in one environment and the other elsewhere.
