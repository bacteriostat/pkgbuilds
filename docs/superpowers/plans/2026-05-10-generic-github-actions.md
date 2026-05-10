# Generic Multi-Package GitHub Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalise the existing joplin-bin GitHub Actions automation to support all GitHub-hosted AUR packages via a config file, adding freetube-bin as the second package.

**Architecture:** A new `packages.yml` config file lists all packages. `check-updates.yml` is rewritten as a two-job workflow — `load-config` parses the YAML and outputs a JSON matrix, `check` runs one parallel job per package. `update-pkgbuild.yml` and `push-to-aur.yml` are refactored to accept a `package` input and operate generically on any package directory.

**Tech Stack:** GitHub Actions, Bash, Python 3 (ubuntu-latest built-in), Docker (archlinux:latest), pacman-contrib, gh CLI, SSH

---

## File Map

| Action | Path |
|--------|------|
| Create | `.github/packages.yml` |
| Modify | `.github/workflows/check-updates.yml` |
| Modify | `.github/workflows/update-pkgbuild.yml` |
| Modify | `.github/workflows/push-to-aur.yml` |
| Modify | `freetube-bin/.SRCINFO` (generate and commit) |

---

## Task 1: Create `.github/packages.yml`

**Files:**
- Create: `.github/packages.yml`

- [ ] **Step 1: Create the config file**

```bash
cat > /home/provost/PersonalProjects/AUR/.github/packages.yml << 'EOF'
packages:
  - name: joplin-bin
    check_type: github
    upstream: laurent22/joplin
    tag_pattern: 's/^v//'
  - name: freetube-bin
    check_type: github
    upstream: FreeTubeApp/FreeTube
    tag_pattern: 's/^v//;s/-beta$//'
EOF
```

- [ ] **Step 2: Verify the file parses correctly**

```bash
python3 -c "
import yaml, json
with open('.github/packages.yml') as f:
    config = yaml.safe_load(f)
pkgs = [p for p in config['packages'] if p.get('check_type') == 'github']
for p in pkgs:
    if 'tag_pattern' not in p:
        p['tag_pattern'] = \"s/^v//\"
print(json.dumps(pkgs, indent=2))
"
```

Expected output:
```json
[
  {
    "name": "joplin-bin",
    "check_type": "github",
    "upstream": "laurent22/joplin",
    "tag_pattern": "s/^v//"
  },
  {
    "name": "freetube-bin",
    "check_type": "github",
    "upstream": "FreeTubeApp/FreeTube",
    "tag_pattern": "s/^v//;s/-beta$//"
  }
]
```

- [ ] **Step 3: Commit**

```bash
git -C /home/provost/PersonalProjects/AUR add .github/packages.yml
git -C /home/provost/PersonalProjects/AUR commit -m "ci: add packages config for generic update automation"
```

---

## Task 2: Rewrite `check-updates.yml`

**Files:**
- Modify: `.github/workflows/check-updates.yml`

This is a complete replacement of the joplin-specific workflow with a two-job matrix-driven workflow.

- [ ] **Step 1: Replace `.github/workflows/check-updates.yml` with the following**

```yaml
name: Check all packages for upstream updates

on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

permissions:
  actions: write
  contents: read

jobs:
  load-config:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.read.outputs.packages }}
    steps:
      - uses: actions/checkout@v4

      - name: Parse packages config
        id: read
        run: |
          PACKAGES=$(python3 -c "
          import yaml, json
          with open('.github/packages.yml') as f:
              config = yaml.safe_load(f)
          pkgs = [p for p in config['packages'] if p.get('check_type') == 'github']
          for p in pkgs:
              if 'tag_pattern' not in p:
                  p['tag_pattern'] = 's/^v//'
          print(json.dumps(pkgs))
          ")
          echo "packages=$PACKAGES" >> "$GITHUB_OUTPUT"

  check:
    needs: load-config
    if: needs.load-config.outputs.packages != '[]'
    strategy:
      matrix:
        package: ${{ fromJSON(needs.load-config.outputs.packages) }}
      fail-fast: false
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Get latest upstream version
        id: upstream
        env:
          UPSTREAM_REPO: ${{ matrix.package.upstream }}
          TAG_PATTERN: ${{ matrix.package.tag_pattern }}
        run: |
          TAG=$(curl -s \
            -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
            -H "Accept: application/vnd.github+json" \
            "https://api.github.com/repos/${UPSTREAM_REPO}/releases/latest" \
            | grep '"tag_name"' \
            | sed 's/.*"tag_name": "\([^"]*\)".*/\1/')
          if [[ -z "$TAG" ]]; then
            echo "ERROR: Failed to get upstream tag for ${UPSTREAM_REPO}" >&2
            exit 1
          fi
          VERSION=$(echo "$TAG" | sed "$TAG_PATTERN")
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

      - name: Get current pkgver
        id: current
        env:
          PACKAGE: ${{ matrix.package.name }}
        run: |
          PKGVER=$(grep '^pkgver=' "${PACKAGE}/PKGBUILD" | cut -d= -f2)
          echo "version=$PKGVER" >> "$GITHUB_OUTPUT"

      - name: Dispatch update if new version found
        if: steps.upstream.outputs.version != steps.current.outputs.version
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          UPSTREAM_VERSION: ${{ steps.upstream.outputs.version }}
          CURRENT_VERSION: ${{ steps.current.outputs.version }}
          PACKAGE: ${{ matrix.package.name }}
        run: |
          echo "New version for ${PACKAGE}: ${UPSTREAM_VERSION} (current: ${CURRENT_VERSION})"
          gh workflow run update-pkgbuild.yml \
            --field "package=${PACKAGE}" \
            --field "version=${UPSTREAM_VERSION}"
```

- [ ] **Step 2: Verify the YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/check-updates.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git -C /home/provost/PersonalProjects/AUR add .github/workflows/check-updates.yml
git -C /home/provost/PersonalProjects/AUR commit -m "ci: rewrite check-updates as generic matrix workflow"
```

---

## Task 3: Refactor `update-pkgbuild.yml`

**Files:**
- Modify: `.github/workflows/update-pkgbuild.yml`

Add a `package` input and replace all hardcoded `joplin-bin` references with `$PACKAGE`.

- [ ] **Step 1: Replace `.github/workflows/update-pkgbuild.yml` with the following**

```yaml
name: Update AUR PKGBUILD

on:
  workflow_dispatch:
    inputs:
      package:
        description: 'Package name (e.g. joplin-bin)'
        required: true
        type: string
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
        env:
          PACKAGE: ${{ inputs.package }}
          VERSION: ${{ inputs.version }}
        run: |
          sed -i "s/^pkgver=.*/pkgver=${VERSION}/" "${PACKAGE}/PKGBUILD"
          sed -i "s/^pkgrel=.*/pkgrel=1/" "${PACKAGE}/PKGBUILD"
          sed -i "s/^md5sums_x86_64=/sha256sums_x86_64=/" "${PACKAGE}/PKGBUILD"

      - name: Run updpkgsums and regenerate .SRCINFO in Arch container
        env:
          WORKSPACE: ${{ github.workspace }}
          PACKAGE: ${{ inputs.package }}
        run: |
          docker run --rm \
            -v "${WORKSPACE}/${PACKAGE}:/pkg" \
            archlinux:latest \
            bash -c "
              pacman -Syu --noconfirm pacman-contrib base-devel &&
              useradd -m builder &&
              chown -R builder /pkg &&
              su builder -c 'cd /pkg && updpkgsums && makepkg --printsrcinfo > .SRCINFO'
            "
          sudo chown -R "$(id -u):$(id -g)" "${PACKAGE}/"

      - name: Create update branch and open PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PACKAGE: ${{ inputs.package }}
          VERSION: ${{ inputs.version }}
        run: |
          git config user.name "bacteriostat"
          git config user.email "dev.bacteriostat@aleeas.com"
          BRANCH="update/${PACKAGE}-v${VERSION}"
          git checkout -b "${BRANCH}" 2>/dev/null || git checkout "${BRANCH}"
          git add "${PACKAGE}/PKGBUILD" "${PACKAGE}/.SRCINFO"
          git commit -m "${PACKAGE}: update to ${VERSION}" || echo "Nothing to commit"
          git push origin "${BRANCH}" --force-with-lease
          if ! gh pr view "${BRANCH}" --json state -q .state 2>/dev/null | grep -q OPEN; then
            gh pr create \
              --title "${PACKAGE}: update to ${VERSION}" \
              --body "Automated update to upstream release v${VERSION}." \
              --base master
          else
            echo "PR for ${BRANCH} already open, skipping creation"
          fi
```

- [ ] **Step 2: Verify the YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/update-pkgbuild.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git -C /home/provost/PersonalProjects/AUR add .github/workflows/update-pkgbuild.yml
git -C /home/provost/PersonalProjects/AUR commit -m "ci: refactor update-pkgbuild to accept package input"
```

---

## Task 4: Refactor `push-to-aur.yml`

**Files:**
- Modify: `.github/workflows/push-to-aur.yml`

Broaden path filter to `*/PKGBUILD`, add `fetch-depth: 2`, detect changed packages via git diff, loop over each.

- [ ] **Step 1: Replace `.github/workflows/push-to-aur.yml` with the following**

```yaml
name: Push packages to AUR

on:
  push:
    branches:
      - master
    paths:
      - '*/PKGBUILD'

jobs:
  push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - name: Setup AUR SSH
        env:
          AUR_SSH_KEY: ${{ secrets.AUR_SSH_KEY }}
        run: |
          mkdir -p ~/.ssh
          echo "$AUR_SSH_KEY" > ~/.ssh/aur
          chmod 600 ~/.ssh/aur
          ssh-keyscan -t ed25519 aur.archlinux.org >> ~/.ssh/known_hosts
          printf 'Host aur.archlinux.org\n  IdentityFile ~/.ssh/aur\n  User aur\n' >> ~/.ssh/config

      - name: Push changed packages to AUR
        run: |
          set -euo pipefail
          CHANGED=$(git diff --name-only HEAD~1 HEAD | grep '/PKGBUILD$' | sed 's|/PKGBUILD$||')
          if [[ -z "$CHANGED" ]]; then
            echo "No PKGBUILD changes detected"
            exit 0
          fi
          for PACKAGE in $CHANGED; do
            echo "Pushing ${PACKAGE} to AUR..."
            git clone "ssh://aur@aur.archlinux.org/${PACKAGE}.git" "/tmp/aur-${PACKAGE}" \
              || { echo "ERROR: Failed to clone AUR repo for ${PACKAGE}"; exit 1; }
            cp "${PACKAGE}/PKGBUILD" "/tmp/aur-${PACKAGE}/"
            cp "${PACKAGE}/.SRCINFO" "/tmp/aur-${PACKAGE}/"
            cd "/tmp/aur-${PACKAGE}"
            git config user.name "bacteriostat"
            git config user.email "dev.bacteriostat@aleeas.com"
            git add PKGBUILD .SRCINFO
            if git diff --quiet --cached; then
              echo "No changes for ${PACKAGE}, skipping"
              cd -
              continue
            fi
            PKGVER=$(grep '^pkgver=' PKGBUILD | cut -d= -f2)
            git commit -m "${PACKAGE}: update to ${PKGVER}"
            git push origin master || { echo "ERROR: Failed to push ${PACKAGE} to AUR"; exit 1; }
            cd -
          done
```

- [ ] **Step 2: Verify the YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/push-to-aur.yml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 3: Commit**

```bash
git -C /home/provost/PersonalProjects/AUR add .github/workflows/push-to-aur.yml
git -C /home/provost/PersonalProjects/AUR commit -m "ci: refactor push-to-aur to support multiple packages"
```

---

## Task 5: Generate freetube-bin `.SRCINFO` and push to GitHub

`freetube-bin/.SRCINFO` does not exist in the repo. `push-to-aur.yml` copies `.SRCINFO` from the repo, so it must be present before any push can succeed.

**Files:**
- Modify: `freetube-bin/.SRCINFO` (generate and commit)

- [ ] **Step 1: Generate `.SRCINFO` using makepkg**

Run from the repo root (requires Arch Linux with `base-devel` installed):

```bash
cd /home/provost/PersonalProjects/AUR/freetube-bin
makepkg --printsrcinfo > .SRCINFO
cd ..
```

Expected: `freetube-bin/.SRCINFO` now exists with content beginning `pkgbase = freetube-bin`.

- [ ] **Step 2: Verify the file looks correct**

```bash
head -10 /home/provost/PersonalProjects/AUR/freetube-bin/.SRCINFO
```

Expected output (approximate):
```
pkgbase = freetube-bin
	pkgdesc = An open source desktop YouTube player built with privacy in mind.
	pkgver = 0.23.15
	pkgrel = 1
	url = https://github.com/FreeTubeApp/FreeTube
	arch = x86_64
	arch = aarch64
```

- [ ] **Step 3: Commit**

```bash
git -C /home/provost/PersonalProjects/AUR add freetube-bin/.SRCINFO
git -C /home/provost/PersonalProjects/AUR commit -m "freetube-bin: add .SRCINFO"
```

- [ ] **Step 4: Push all commits to GitHub**

```bash
git -C /home/provost/PersonalProjects/AUR push origin master
```

- [ ] **Step 5: Test `update-pkgbuild.yml` with freetube-bin**

In the GitHub web UI: repo → **Actions** → **Update AUR PKGBUILD** → **Run workflow**

- `package`: `freetube-bin`
- `version`: `0.23.15` (current version — tests the workflow end-to-end without a real update)

Expected: workflow runs, Arch container computes sha256sums for both x86_64 and aarch64, generates `.SRCINFO`, opens a PR titled `"freetube-bin: update to 0.23.15"`.

Close the test PR without merging.

- [ ] **Step 6: Test `check-updates.yml` matrix behaviour**

In the GitHub web UI: repo → **Actions** → **Check all packages for upstream updates** → **Run workflow**

Expected: two parallel `check` jobs appear (one for `joplin-bin`, one for `freetube-bin`). Both read their current pkgver and compare against upstream. No dispatch if both are up to date.
