# joplin-bin GitHub Actions — Design Spec

**Date:** 2026-05-10
**Status:** Approved

## Goal

Automate PKGBUILD updates for `joplin-bin` using GitHub Actions. New Joplin releases are detected automatically and a PR is opened for review. Merging the PR triggers an automatic push to AUR.

## Flow

```
[daily cron] → check-updates.yml
     ↓ new version detected
update-pkgbuild.yml (workflow_dispatch)
     ↓ opens PR: "joplin-bin: update to vX.X.X"
[manual review + merge]
     ↓ push to master, joplin-bin/** changed
push-to-aur.yml
     ↓ pushes PKGBUILD + .SRCINFO to AUR
```

## Workflow Files

### 1. `check-updates.yml`

**Trigger:** Daily cron (`0 6 * * *`) + `workflow_dispatch` for manual runs.

**Runner:** `ubuntu-latest`

**Permissions:** `actions: write` (required to dispatch `update-pkgbuild.yml`)

**Steps:**
1. Checkout repo
2. Query GitHub API (`/repos/laurent22/joplin/releases/latest`), extract version (strip leading `v`), using `GITHUB_TOKEN` to avoid rate limits
3. Read current `pkgver` from `joplin-bin/PKGBUILD` via `grep`
4. If versions differ: trigger `update-pkgbuild.yml` via `workflow_dispatch` with `version` input
5. If same: exit cleanly (no-op)

### 2. `update-pkgbuild.yml`

**Trigger:** `workflow_dispatch` with required string input `version` (e.g. `3.6.12`). Can also be run manually to force an update.

**Runner:** `ubuntu-latest`, container `archlinux:latest`

**Steps:**
1. Checkout repo (with write permissions via `GITHUB_TOKEN`)
2. Install `base-devel` + `pacman-contrib` (provides `updpkgsums` and `makepkg`)
3. Update `pkgver` to `{version}`, `pkgrel` to `1`, and rename `md5sums_x86_64` to `sha256sums_x86_64` in `joplin-bin/PKGBUILD` via `sed`
4. Run `updpkgsums` inside `joplin-bin/` — downloads sources defined in PKGBUILD, computes checksums, and fills in the `sha256sums_x86_64` value in-place (`updpkgsums` updates whatever checksum variable is present, so the rename in step 3 must happen first)
5. Run `makepkg --printsrcinfo > .SRCINFO` inside `joplin-bin/`
6. Create branch `update/joplin-bin-v{version}`
7. Commit: `"joplin-bin: update to {version}"`
8. Push branch
9. Open PR via `gh` CLI: title `"joplin-bin: update to {version}"`

### 3. `push-to-aur.yml`

**Trigger:** `push` to `master`, path filter `joplin-bin/**`

**Runner:** `ubuntu-latest` (no Arch container needed — git + SSH only)

**Steps:**
1. Checkout repo
2. Write `AUR_SSH_KEY` secret to `~/.ssh/aur`, chmod `600`
3. Configure `~/.ssh/config` to use that key for `aur.archlinux.org`
4. Add `aur.archlinux.org` to `~/.ssh/known_hosts` via `ssh-keyscan`
5. Clone `ssh://aur@aur.archlinux.org/joplin-bin.git` into a temp dir
6. Copy `joplin-bin/PKGBUILD` + `joplin-bin/.SRCINFO` into the clone
7. Set git user matching the PKGBUILD maintainer line (`bacteriostat`, `dev dot bacteriostat at aleeas dot com`)
8. Read `pkgver` from PKGBUILD; commit: `"joplin-bin: update to {pkgver}"`
9. Push to AUR `master`

## Secrets Required

| Secret | Purpose |
|--------|---------|
| `AUR_SSH_KEY` | AUR private key (contents of `~/.ssh/aur`) |
| `GITHUB_TOKEN` | Automatic — used for API calls and PR creation |

## PKGBUILD Changes

As part of the first automated update, `md5sums_x86_64` is replaced with `sha256sums_x86_64`. AUR recommends sha256; md5 is deprecated.

## Future Extension

The `check-updates.yml` and `update-pkgbuild.yml` workflows are intentionally focused on `joplin-bin`. When other packages are added to this automation, a config file (e.g. `packages.yml`) can drive a matrix strategy across all packages, replacing per-package hardcoded logic.
