# Generic Multi-Package GitHub Actions — Design Spec

**Date:** 2026-05-10
**Status:** Approved

## Goal

Generalise the joplin-bin GitHub Actions automation to support all GitHub-hosted AUR packages via a single config file. Adding a new package requires only a two-line entry in `packages.yml` — no new workflow files.

## Packages in Scope

| Package | Upstream | Tag pattern |
|---------|----------|-------------|
| `joplin-bin` | `laurent22/joplin` | `s/^v//` |
| `freetube-bin` | `FreeTubeApp/FreeTube` | `s/^v//;s/-beta$//` |

Non-GitHub packages (e.g. xmind) are out of scope — to be handled separately when needed.

## Config File

**`.github/packages.yml`**

```yaml
packages:
  - name: joplin-bin
    check_type: github
    upstream: laurent22/joplin
    tag_pattern: 's/^v//'
  - name: freetube-bin
    check_type: github
    upstream: FreeTubeApp/FreeTube
    tag_pattern: 's/^v//;s/-beta$//'
```

`tag_pattern` is a sed expression applied to the raw GitHub tag to produce the pkgver. Required for all `check_type: github` entries.

## Flow

```
[daily cron] → check-updates.yml
     ↓ reads packages.yml, spins one check job per package (parallel)
     ↓ for each: compare upstream tag vs PKGBUILD pkgver
     ↓ if behind: dispatch update-pkgbuild.yml(package, version)
update-pkgbuild.yml
     ↓ updates {package}/PKGBUILD + .SRCINFO, opens PR
[manual review + merge]
     ↓ push to master, */PKGBUILD changed
push-to-aur.yml
     ↓ detects changed packages, pushes each to AUR
```

## Workflow Files

### 1. `check-updates.yml` (refactored)

**Trigger:** Daily cron (`0 6 * * *`) + `workflow_dispatch`

**Permissions:** `actions: write`, `contents: read`

**Job 1 — `load-config`:**
- Checkout repo
- Parse `.github/packages.yml` with Python (`yaml` is available on ubuntu-latest)
- Filter to `check_type: github` entries only
- Ensure every entry has `tag_pattern` set (default `'s/^v//'` if missing)
- Output JSON array as `packages` step output

**Job 2 — `check` (matrix, `fail-fast: false`):**
- Matrix driven by `fromJSON(needs.load-config.outputs.packages)`
- One job per package, runs in parallel
- Steps:
  1. Checkout repo
  2. Fetch latest tag from GitHub API using `UPSTREAM_REPO` env var; validate non-empty
  3. Apply `TAG_PATTERN` (from matrix) via sed to extract version
  4. Read current pkgver from `{package}/PKGBUILD`
  5. If versions differ: `gh workflow run update-pkgbuild.yml --field package=... --field version=...`

**Security:** All `${{ matrix.package.* }}` expressions passed to shell via env vars, not inline.

### 2. `update-pkgbuild.yml` (refactored)

**Trigger:** `workflow_dispatch` with inputs:
- `package` (required string) — e.g. `joplin-bin`
- `version` (required string) — e.g. `3.6.12`

**Permissions:** `contents: write`, `pull-requests: write`

**Steps:**
1. Checkout repo
2. `sed` to update `pkgver`, `pkgrel=1`, rename `md5sums_*` → `sha256sums_*` in `{package}/PKGBUILD` — all via `$PACKAGE`/`$VERSION` env vars
3. `docker run archlinux:latest` with `{package}/` volume-mounted — install `pacman-contrib` + `base-devel` (`pacman -Syu`), create non-root builder user, run `updpkgsums && makepkg --printsrcinfo > .SRCINFO`
4. `sudo chown -R "$(id -u):$(id -g)" {package}/`
5. Branch `update/{package}-v{version}`, commit, push, `gh pr create`; branch/PR collision guards in place

### 3. `push-to-aur.yml` (refactored)

**Trigger:** `push` to `master`, path filter `*/PKGBUILD`

**Permissions:** none beyond default (git + SSH only)

**Checkout:** `fetch-depth: 2` (needed for `HEAD~1` diff)

**Steps:**
1. Checkout repo with `fetch-depth: 2`
2. Setup AUR SSH — key from `AUR_SSH_KEY` secret via env var, `ssh-keyscan`, `~/.ssh/config`
3. Detect changed packages: `git diff --name-only HEAD~1 HEAD | grep '/PKGBUILD$' | sed 's|/PKGBUILD$||'`
4. For each changed package (bash loop):
   - Clone `ssh://aur@aur.archlinux.org/${PACKAGE}.git` to `/tmp/aur-${PACKAGE}`
   - Copy `{package}/PKGBUILD` and `{package}/.SRCINFO`
   - `git add`, check `git diff --quiet --cached` (skip if no changes)
   - Commit `"{package}: update to {pkgver}"`, push; error message on failure

## Files Changed

| Action | Path |
|--------|------|
| Create | `.github/packages.yml` |
| Modify | `.github/workflows/check-updates.yml` |
| Modify | `.github/workflows/update-pkgbuild.yml` |
| Modify | `.github/workflows/push-to-aur.yml` |
