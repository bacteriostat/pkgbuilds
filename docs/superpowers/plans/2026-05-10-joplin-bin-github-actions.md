# joplin-bin GitHub Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate joplin-bin PKGBUILD updates — a daily check opens a PR when a new Joplin release is found, and merging the PR automatically pushes to AUR.

**Architecture:** Three workflow files with a single responsibility each: `check-updates.yml` detects new versions and dispatches, `update-pkgbuild.yml` mutates PKGBUILD + .SRCINFO and opens a PR, `push-to-aur.yml` pushes to AUR on master merge. Arch-specific tooling (`updpkgsums`, `makepkg`) runs inside a `docker run archlinux:latest` step on the ubuntu runner to avoid container compatibility issues with JS actions.

**Tech Stack:** GitHub Actions, Bash, Docker (archlinux:latest), pacman-contrib (`updpkgsums`), gh CLI (pre-installed on ubuntu-latest), SSH (AUR key stored as secret)

---

## File Map

| Action | Path |
|--------|------|
| Create | `.github/workflows/check-updates.yml` |
| Create | `.github/workflows/update-pkgbuild.yml` |
| Create | `.github/workflows/push-to-aur.yml` |

---

## Task 1: Create `check-updates.yml`

**Files:**
- Create: `.github/workflows/check-updates.yml`

- [ ] **Step 1: Create the `.github/workflows` directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Verify the Joplin releases API returns a parseable tag**

Run this locally to confirm the API shape before writing the workflow:

```bash
curl -s https://api.github.com/repos/laurent22/joplin/releases/latest \
  | grep '"tag_name"' \
  | sed 's/.*"v\([^"]*\)".*/\1/'
```

Expected output: a version string like `3.6.12` (no `v` prefix).

- [ ] **Step 3: Create `.github/workflows/check-updates.yml`**

```yaml
name: Check joplin-bin for upstream updates

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

permissions:
  actions: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Get latest Joplin release version
        id: upstream
        run: |
          VERSION=$(curl -s \
            -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/laurent22/joplin/releases/latest \
            | grep '"tag_name"' \
            | sed 's/.*"v\([^"]*\)".*/\1/')
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Get current pkgver
        id: current
        run: |
          PKGVER=$(grep '^pkgver=' joplin-bin/PKGBUILD | cut -d= -f2)
          echo "version=$PKGVER" >> "$GITHUB_OUTPUT"

      - name: Dispatch update workflow if new version found
        if: steps.upstream.outputs.version != steps.current.outputs.version
        run: |
          echo "New version: ${{ steps.upstream.outputs.version }} (current: ${{ steps.current.outputs.version }})"
          gh workflow run update-pkgbuild.yml \
            --field version=${{ steps.upstream.outputs.version }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/check-updates.yml
git commit -m "ci: add check-updates workflow for joplin-bin"
```

---

## Task 2: Create `update-pkgbuild.yml`

**Files:**
- Create: `.github/workflows/update-pkgbuild.yml`

- [ ] **Step 1: Verify the docker command works locally**

This confirms `updpkgsums` can run inside an Arch container before wiring it into the workflow. Run from the repo root:

```bash
sed -i "s/^md5sums_x86_64=/sha256sums_x86_64=/" joplin-bin/PKGBUILD
docker run --rm \
  -v "$PWD/joplin-bin:/pkg" \
  archlinux:latest \
  bash -c "
    pacman -Sy --noconfirm pacman-contrib base-devel &&
    useradd -m builder &&
    chown -R builder /pkg &&
    su builder -c 'cd /pkg && updpkgsums && makepkg --printsrcinfo > .SRCINFO'
  "
```

Expected: PKGBUILD now has `sha256sums_x86_64=(...)` with a valid hash; `.SRCINFO` is regenerated.

Fix permissions after verifying:

```bash
sudo chown -R "$(id -u):$(id -g)" joplin-bin/
```

Revert the local PKGBUILD change (the workflow will handle this):

```bash
git checkout joplin-bin/PKGBUILD joplin-bin/.SRCINFO
```

- [ ] **Step 2: Create `.github/workflows/update-pkgbuild.yml`**

```yaml
name: Update joplin-bin PKGBUILD

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'New version number (e.g. 3.6.12)'
        required: true
        type: string

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Update pkgver, pkgrel, and switch md5 to sha256
        run: |
          sed -i "s/^pkgver=.*/pkgver=${{ inputs.version }}/" joplin-bin/PKGBUILD
          sed -i "s/^pkgrel=.*/pkgrel=1/" joplin-bin/PKGBUILD
          sed -i "s/^md5sums_x86_64=/sha256sums_x86_64=/" joplin-bin/PKGBUILD

      - name: Run updpkgsums and regenerate .SRCINFO in Arch container
        run: |
          docker run --rm \
            -v "${{ github.workspace }}/joplin-bin:/pkg" \
            archlinux:latest \
            bash -c "
              pacman -Sy --noconfirm pacman-contrib base-devel &&
              useradd -m builder &&
              chown -R builder /pkg &&
              su builder -c 'cd /pkg && updpkgsums && makepkg --printsrcinfo > .SRCINFO'
            "
          sudo chown -R "$(id -u):$(id -g)" joplin-bin/

      - name: Create update branch and open PR
        run: |
          git config user.name "bacteriostat"
          git config user.email "dev.bacteriostat@aleeas.com"
          git checkout -b "update/joplin-bin-v${{ inputs.version }}"
          git add joplin-bin/PKGBUILD joplin-bin/.SRCINFO
          git commit -m "joplin-bin: update to ${{ inputs.version }}"
          git push origin "update/joplin-bin-v${{ inputs.version }}"
          gh pr create \
            --title "joplin-bin: update to ${{ inputs.version }}" \
            --body "Automated update to upstream release v${{ inputs.version }}." \
            --base master
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update-pkgbuild.yml
git commit -m "ci: add update-pkgbuild workflow for joplin-bin"
```

---

## Task 3: Create `push-to-aur.yml`

**Files:**
- Create: `.github/workflows/push-to-aur.yml`

- [ ] **Step 1: Create `.github/workflows/push-to-aur.yml`**

```yaml
name: Push joplin-bin to AUR

on:
  push:
    branches:
      - master
    paths:
      - 'joplin-bin/**'

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup AUR SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.AUR_SSH_KEY }}" > ~/.ssh/aur
          chmod 600 ~/.ssh/aur
          ssh-keyscan -t ed25519 aur.archlinux.org >> ~/.ssh/known_hosts
          printf 'Host aur.archlinux.org\n  IdentityFile ~/.ssh/aur\n  User aur\n' >> ~/.ssh/config

      - name: Clone AUR repo
        run: git clone ssh://aur@aur.archlinux.org/joplin-bin.git /tmp/aur-joplin-bin

      - name: Copy updated files
        run: |
          cp joplin-bin/PKGBUILD /tmp/aur-joplin-bin/
          cp joplin-bin/.SRCINFO /tmp/aur-joplin-bin/

      - name: Commit and push to AUR
        run: |
          cd /tmp/aur-joplin-bin
          git config user.name "bacteriostat"
          git config user.email "dev.bacteriostat@aleeas.com"
          git add PKGBUILD .SRCINFO
          if git diff --quiet --cached; then
            echo "No changes to push to AUR"
            exit 0
          fi
          PKGVER=$(grep '^pkgver=' PKGBUILD | cut -d= -f2)
          git commit -m "joplin-bin: update to ${PKGVER}"
          git push origin master
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/push-to-aur.yml
git commit -m "ci: add push-to-aur workflow for joplin-bin"
```

---

## Task 4: Add AUR SSH Key Secret

**This is a manual step in the GitHub UI.**

- [ ] **Step 1: Copy the AUR private key contents**

```bash
cat ~/.ssh/aur
```

Copy the entire output including the `-----BEGIN...` and `-----END...` lines.

- [ ] **Step 2: Add the secret to the GitHub repo**

In the GitHub web UI: repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

- Name: `AUR_SSH_KEY`
- Value: paste the key contents from Step 1
- Click **Add secret**

- [ ] **Step 3: Verify the secret appears in the secrets list**

On the same Secrets page, `AUR_SSH_KEY` should appear in the repository secrets list.

---

## Task 5: End-to-End Test

- [ ] **Step 1: Push all three workflow files to master**

```bash
git push origin master
```

- [ ] **Step 2: Manually trigger `update-pkgbuild.yml` with the current version to test PR creation**

In the GitHub web UI: repo → **Actions** → **Update joplin-bin PKGBUILD** → **Run workflow**

Enter the current `pkgver` from `joplin-bin/PKGBUILD` as the version, click **Run workflow**.

Expected: workflow completes, a PR is opened titled `"joplin-bin: update to {version}"` with PKGBUILD and .SRCINFO changes using sha256sums.

- [ ] **Step 3: Close the test PR without merging**

The test PR is just to verify the workflow ran correctly. Close it without merging.

- [ ] **Step 4: Manually trigger `check-updates.yml` to verify the version comparison logic**

In the GitHub web UI: repo → **Actions** → **Check joplin-bin for upstream updates** → **Run workflow**

Expected: if joplin-bin is up to date, the workflow exits cleanly with no dispatch. Check the run logs to confirm the upstream and current versions were read correctly.

- [ ] **Step 5: Verify `push-to-aur.yml` triggers on next joplin-bin merge**

The next time a PR touching `joplin-bin/**` is merged to master, verify in the Actions tab that `push-to-aur.yml` runs and the AUR repo is updated.
