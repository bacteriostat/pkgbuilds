# Design: Extract Complex Workflow Bash into Python Scripts

**Date:** 2026-05-13

## Goal

Replace complex multi-line bash and inline Python in GitHub Actions workflows with readable `.github/scripts/*.py` files. Short, self-explanatory bash steps stay as-is. The step-by-step structure of each workflow remains visible in the YAML.

## Scope

Four scripts extracted into `.github/scripts/`:

| Script | Workflow | Step replaced |
|---|---|---|
| `parse_packages.py` | `check-updates.yml` / `load-config` job | `Parse packages config` — big `python3 -c "..."` inline |
| `check_version.py` | `check-updates.yml` / `check` job | `Get latest upstream version` — if/elif curl/grep/sed |
| `push_to_aur.py` | `push-to-aur.yml` | `Push changed packages to AUR` — loop with error accumulation |
| `create_pr.py` | `update-pkgbuild.yml` | `Create update branch and open PR` — git + gh conditionals |

Steps that stay as bash: SSH setup, `sed` pkgver/pkgrel replacements, `docker run`, `gh workflow run` dispatch, `grep`/`cut` pkgver read.

## Conventions

- **Inputs:** environment variables (same names already used in the workflow `env:` blocks).
- **Outputs:** write to `$GITHUB_OUTPUT` via `os.environ['GITHUB_OUTPUT']` file appends where the step currently does `echo "key=value" >> "$GITHUB_OUTPUT"`.
- **Errors:** print to `sys.stderr` and `sys.exit(1)` — mirrors existing `exit 1` behaviour.
- **External tools:** `git`, `gh`, `docker` still invoked via `subprocess.run()` with `check=True`.
- **Dependencies:** stdlib only (`urllib.request`, `subprocess`, `os`, `re`, `json`, `pathlib`). `yaml` is available as `python3-yaml` on `ubuntu-latest`.
- **Workflow call site:** each replaced step becomes `run: python3 .github/scripts/<script>.py` with its existing `env:` block unchanged.

## Script details

### `parse_packages.py`
- Reads `.github/packages.yml` using `yaml.safe_load`.
- Filters to packages where `check_type` is one of `github`, `gitlab`, `xmind_custom`.
- Applies defaults: `tag_pattern = 's/^v//'`, `release_type = 'latest'`, `pkgver_var = 'pkgver'`.
- Writes `packages=<json>` to `$GITHUB_OUTPUT`.

### `check_version.py`
Env vars read: `CHECK_TYPE`, `UPSTREAM_REPO`, `TAG_PATTERN`, `RELEASE_TYPE`, `REDIRECT_URL`, `FILENAME_PREFIX`, `GITHUB_TOKEN`, `GITHUB_OUTPUT`.

- Branches on `CHECK_TYPE`:
  - `xmind_custom`: follows redirect via `urllib.request`, strips filename prefix.
  - `gitlab`: calls GitLab tags API, extracts first tag name.
  - `github` (any): calls GitHub releases API with `per_page=1`, extracts `tag_name`.
  - `github` (latest): calls GitHub releases/latest API, extracts `tag_name`.
- Applies `TAG_PATTERN` (a sed expression) by piping the tag string through `subprocess.run(['sed', tag_pattern], ...)` — avoids reimplementing sed syntax in Python.
- Validates version is non-empty and not `"null"`.
- Writes `version=<upstream>` to `$GITHUB_OUTPUT`.

### `push_to_aur.py`
Env vars read: none beyond the runner environment (git and ssh already configured by prior steps).

- Finds changed PKGBUILDs: `git diff --name-only HEAD~1 HEAD`, filtered to `*/PKGBUILD` excluding `archive/`.
- For each package: clones AUR repo, checks `.SRCINFO` exists, copies `PKGBUILD` and `.SRCINFO`, configures git identity, commits, pushes.
- Accumulates failures; exits 1 with a summary if any package failed.

### `create_pr.py`
Env vars read: `PACKAGE`, `VERSION`, `GH_TOKEN`, `AUR_USER_NAME`, `AUR_USER_EMAIL` (the latter two added to the step's `env:` block — they are currently interpolated directly into the bash `git config` calls inside this step, so they move into the script).

- Calls `git config user.name` / `git config user.email` via subprocess using those env vars.

- Reads actual `pkgver` from `<PACKAGE>/.SRCINFO` (post-docker-run value).
- Constructs branch name `update/<package>-v<pkgver>`.
- Checks out or creates the branch.
- Stages `PKGBUILD` and `.SRCINFO`; skips commit if nothing changed.
- Force-pushes with `--force-with-lease`.
- Checks for existing open PR via `gh pr list`; creates one if absent.

## What does NOT change

- Workflow trigger/schedule/permissions/concurrency blocks.
- The `load-config` → `check` job dependency and matrix strategy.
- The `if: steps.upstream.outputs.version != steps.current.outputs.version` condition (still uses step outputs from `check_version.py`).
- SSH setup step in `push-to-aur.yml`.
- `sed` pkgver/pkgrel replacement and `docker run` steps in `update-pkgbuild.yml`.
- `Get current pkgver` and `Dispatch update` steps in `check-updates.yml`.
