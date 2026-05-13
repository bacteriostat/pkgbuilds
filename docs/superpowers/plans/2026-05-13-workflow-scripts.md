# Workflow Bash → Python Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace complex multi-line bash and inline Python in three GitHub Actions workflows with readable `.github/scripts/*.py` files, keeping the step-by-step structure of each workflow YAML intact.

**Architecture:** Each script exposes pure helper functions (testable with pytest) plus a `main()` entry point that reads env vars and calls the helpers. Scripts are invoked with `python3 .github/scripts/<script>.py`; existing `env:` blocks in workflow steps are kept unchanged except where variables were previously interpolated directly in bash rather than passed as env vars.

**Tech Stack:** Python 3 stdlib only (`urllib.request`, `subprocess`, `os`, `json`, `pathlib`); `pyyaml` (pre-installed on ubuntu-latest); `pytest` + `pytest-mock` for tests.

---

## File Map

**Create:**
- `.github/scripts/parse_packages.py` — filters and normalises packages from `packages.yml`
- `.github/scripts/check_version.py` — fetches upstream version for github / gitlab / xmind_custom
- `.github/scripts/push_to_aur.py` — clones AUR repos, copies files, commits and pushes
- `.github/scripts/create_pr.py` — creates update branch and opens GitHub PR
- `.github/scripts/tests/conftest.py` — adds scripts dir to sys.path for test imports
- `.github/scripts/tests/test_parse_packages.py`
- `.github/scripts/tests/test_check_version.py`
- `.github/scripts/tests/test_push_to_aur.py`
- `.github/scripts/tests/test_create_pr.py`

**Modify:**
- `.github/workflows/check-updates.yml` — replace `Parse packages config` run block; replace `Get latest upstream version` run block and add `GITHUB_TOKEN` to its env
- `.github/workflows/push-to-aur.yml` — replace `Push changed packages to AUR` run block; add `AUR_USER_NAME` / `AUR_USER_EMAIL` to env (currently hardcoded in bash)
- `.github/workflows/update-pkgbuild.yml` — replace `Create update branch and open PR` run block; add `AUR_USER_NAME` / `AUR_USER_EMAIL` to env (currently interpolated inline in bash)

---

### Task 1: Test infrastructure

**Files:**
- Create: `.github/scripts/tests/conftest.py`

- [ ] **Step 1: Install test dependencies**

```bash
pip install pytest pytest-mock pyyaml
```

- [ ] **Step 2: Create test directory and conftest**

Create `.github/scripts/tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
```

- [ ] **Step 3: Verify pytest discovers tests**

```bash
cd .github/scripts && pytest tests/ --collect-only
```

Expected: exits with code 5 (`no tests ran`) — no test files yet, that's fine.

- [ ] **Step 4: Commit**

```bash
git add .github/scripts/tests/conftest.py
git commit -m "test: add pytest infrastructure for workflow scripts"
```

---

### Task 2: parse_packages.py

**Files:**
- Create: `.github/scripts/parse_packages.py`
- Create: `.github/scripts/tests/test_parse_packages.py`
- Modify: `.github/workflows/check-updates.yml`

- [ ] **Step 1: Write the failing tests**

Create `.github/scripts/tests/test_parse_packages.py`:

```python
import yaml
from parse_packages import load_packages


def test_filters_to_supported_check_types(tmp_path):
    config_file = tmp_path / "packages.yml"
    config_file.write_text(yaml.dump({
        "packages": [
            {"name": "a", "check_type": "github", "upstream": "user/a"},
            {"name": "b", "check_type": "gitlab", "upstream": "user/b"},
            {"name": "c", "check_type": "xmind_custom", "url": "http://x"},
            {"name": "d", "check_type": "manual"},
        ]
    }))
    pkgs = load_packages(str(config_file))
    assert [p["name"] for p in pkgs] == ["a", "b", "c"]


def test_applies_defaults(tmp_path):
    config_file = tmp_path / "packages.yml"
    config_file.write_text(yaml.dump({
        "packages": [{"name": "a", "check_type": "github", "upstream": "user/a"}]
    }))
    pkgs = load_packages(str(config_file))
    assert pkgs[0]["tag_pattern"] == "s/^v//"
    assert pkgs[0]["release_type"] == "latest"
    assert pkgs[0]["pkgver_var"] == "pkgver"


def test_preserves_existing_values(tmp_path):
    config_file = tmp_path / "packages.yml"
    config_file.write_text(yaml.dump({
        "packages": [{
            "name": "a",
            "check_type": "github",
            "upstream": "user/a",
            "tag_pattern": "s/^myapp-//",
            "release_type": "any",
            "pkgver_var": "mypkgver",
        }]
    }))
    pkgs = load_packages(str(config_file))
    assert pkgs[0]["tag_pattern"] == "s/^myapp-//"
    assert pkgs[0]["release_type"] == "any"
    assert pkgs[0]["pkgver_var"] == "mypkgver"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd .github/scripts && pytest tests/test_parse_packages.py -v
```

Expected: `ImportError: No module named 'parse_packages'`

- [ ] **Step 3: Write parse_packages.py**

Create `.github/scripts/parse_packages.py`:

```python
import json
import os

import yaml


def load_packages(config_path: str) -> list:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    pkgs = [
        p for p in config["packages"]
        if p.get("check_type") in ("github", "gitlab", "xmind_custom")
    ]
    for p in pkgs:
        p.setdefault("tag_pattern", "s/^v//")
        p.setdefault("release_type", "latest")
        p.setdefault("pkgver_var", "pkgver")
    return pkgs


def main() -> None:
    pkgs = load_packages(".github/packages.yml")
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"packages={json.dumps(pkgs)}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd .github/scripts && pytest tests/test_parse_packages.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Update check-updates.yml — Parse packages config step**

In `.github/workflows/check-updates.yml`, replace the entire `run:` block of the `Parse packages config` step:

Before:
```yaml
      - name: Parse packages config
        id: read
        run: |
          PACKAGES=$(python3 -c "
          import yaml, json
          with open('.github/packages.yml') as f:
              config = yaml.safe_load(f)
          pkgs = [p for p in config['packages'] if p.get('check_type') in ('github', 'gitlab', 'xmind_custom')]
          for p in pkgs:
              if 'tag_pattern' not in p:
                  p['tag_pattern'] = 's/^v//'
              if 'release_type' not in p:
                  p['release_type'] = 'latest'
              if 'pkgver_var' not in p:
                  p['pkgver_var'] = 'pkgver'
          print(json.dumps(pkgs))
          ")
          echo "packages=$PACKAGES" >> "$GITHUB_OUTPUT"
```

After:
```yaml
      - name: Parse packages config
        id: read
        run: python3 .github/scripts/parse_packages.py
```

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/parse_packages.py .github/scripts/tests/test_parse_packages.py .github/workflows/check-updates.yml
git commit -m "feat: extract parse_packages.py from check-updates workflow"
```

---

### Task 3: check_version.py

**Files:**
- Create: `.github/scripts/check_version.py`
- Create: `.github/scripts/tests/test_check_version.py`
- Modify: `.github/workflows/check-updates.yml`

- [ ] **Step 1: Write the failing tests**

Create `.github/scripts/tests/test_check_version.py`:

```python
import json
import urllib.error
from email.message import Message
from unittest.mock import MagicMock

import pytest

from check_version import apply_tag_pattern, fetch_github_version, fetch_gitlab_version, fetch_xmind_version


def test_apply_tag_pattern_strips_v_prefix():
    assert apply_tag_pattern("v1.2.3", "s/^v//") == "1.2.3"


def test_apply_tag_pattern_no_prefix_to_strip():
    assert apply_tag_pattern("1.2.3", "s/^v//") == "1.2.3"


def test_fetch_xmind_version(mocker):
    headers = Message()
    headers["Location"] = "https://dl.xmind.net/Xmind-for-Linux-xmind-26.03.04129.deb"
    exc = urllib.error.HTTPError("http://x", 302, "Found", headers, None)
    mock_opener = MagicMock()
    mock_opener.open.side_effect = exc
    mocker.patch("check_version.urllib.request.build_opener", return_value=mock_opener)
    assert fetch_xmind_version("http://x", "Xmind-for-Linux-xmind-") == "26.03.04129"


def test_fetch_gitlab_version(mocker):
    response_data = json.dumps([{"name": "v2.1.0"}]).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mocker.patch("check_version.urllib.request.urlopen", return_value=mock_resp)
    assert fetch_gitlab_version("user/repo", "s/^v//") == "2.1.0"


def test_fetch_github_latest(mocker):
    response_data = json.dumps({"tag_name": "v3.5.0"}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mocker.patch("check_version.urllib.request.urlopen", return_value=mock_resp)
    assert fetch_github_version("user/repo", "s/^v//", "latest", "token") == "3.5.0"


def test_fetch_github_any(mocker):
    response_data = json.dumps([{"tag_name": "v4.0.0-beta"}]).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_data
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mocker.patch("check_version.urllib.request.urlopen", return_value=mock_resp)
    assert fetch_github_version("user/repo", "s/^v//", "any", "token") == "4.0.0-beta"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd .github/scripts && pytest tests/test_check_version.py -v
```

Expected: `ImportError: No module named 'check_version'`

- [ ] **Step 3: Write check_version.py**

Create `.github/scripts/check_version.py`:

```python
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)
    http_error_302 = http_error_303 = http_error_307 = http_error_301


def apply_tag_pattern(tag: str, pattern: str) -> str:
    result = subprocess.run(
        ["sed", pattern], input=tag, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def fetch_xmind_version(redirect_url: str, filename_prefix: str) -> str:
    opener = urllib.request.build_opener(_NoRedirectHandler())
    try:
        opener.open(redirect_url)
        raise RuntimeError(f"Expected redirect from {redirect_url} but got none")
    except urllib.error.HTTPError as e:
        dest = e.headers.get("Location", "")
    if not dest:
        raise RuntimeError(f"No redirect URL from {redirect_url}")
    name = os.path.basename(dest)
    if name.endswith(".deb"):
        name = name[:-4]
    return name[len(filename_prefix):] if name.startswith(filename_prefix) else name


def fetch_gitlab_version(upstream_repo: str, tag_pattern: str) -> str:
    encoded = upstream_repo.replace("/", "%2F")
    url = f"https://gitlab.com/api/v4/projects/{encoded}/repository/tags?per_page=1"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())
    return apply_tag_pattern(data[0]["name"], tag_pattern)


def fetch_github_version(
    upstream_repo: str, tag_pattern: str, release_type: str, token: str
) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    if release_type == "any":
        url = f"https://api.github.com/repos/{upstream_repo}/releases?per_page=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        tag = data[0]["tag_name"]
    else:
        url = f"https://api.github.com/repos/{upstream_repo}/releases/latest"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        tag = data["tag_name"]
    return apply_tag_pattern(tag, tag_pattern)


def main() -> None:
    check_type = os.environ["CHECK_TYPE"]
    tag_pattern = os.environ.get("TAG_PATTERN", "s/^v//")

    if check_type == "xmind_custom":
        version = fetch_xmind_version(
            os.environ["REDIRECT_URL"],
            os.environ.get("FILENAME_PREFIX", ""),
        )
    elif check_type == "gitlab":
        version = fetch_gitlab_version(os.environ["UPSTREAM_REPO"], tag_pattern)
    else:
        version = fetch_github_version(
            os.environ["UPSTREAM_REPO"],
            tag_pattern,
            os.environ.get("RELEASE_TYPE", "latest"),
            os.environ["GITHUB_TOKEN"],
        )

    if not version:
        print("ERROR: Failed to determine upstream version", file=sys.stderr)
        sys.exit(1)
    if version == "null":
        print("ERROR: No releases found upstream", file=sys.stderr)
        sys.exit(1)

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"version={version}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd .github/scripts && pytest tests/test_check_version.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Update check-updates.yml — Get latest upstream version step**

In `.github/workflows/check-updates.yml`, replace the `Get latest upstream version` step. Add `GITHUB_TOKEN` to the `env:` block (previously it was interpolated inline in the bash as `${{ secrets.GITHUB_TOKEN }}`):

Before:
```yaml
      - name: Get latest upstream version
        id: upstream
        env:
          UPSTREAM_REPO: ${{ matrix.package.upstream }}
          TAG_PATTERN: ${{ matrix.package.tag_pattern }}
          RELEASE_TYPE: ${{ matrix.package.release_type }}
          CHECK_TYPE: ${{ matrix.package.check_type }}
          REDIRECT_URL: ${{ matrix.package.url }}
          FILENAME_PREFIX: ${{ matrix.package.filename_prefix }}
        run: |
          if [[ "${CHECK_TYPE}" == "xmind_custom" ]]; then
            DEST=$(curl -sSf -o /dev/null -w '%{redirect_url}' "${REDIRECT_URL}")
            if [[ -z "$DEST" ]]; then
              echo "ERROR: No redirect from ${REDIRECT_URL}" >&2
              exit 1
            fi
            FILENAME=$(basename "$DEST" .deb)
            VERSION="${FILENAME#${FILENAME_PREFIX}}"
          elif [[ "${CHECK_TYPE}" == "gitlab" ]]; then
            ENCODED_REPO="${UPSTREAM_REPO/\//%2F}"
            TAG=$(curl -s \
              "https://gitlab.com/api/v4/projects/${ENCODED_REPO}/repository/tags?per_page=1" \
              | grep -oP '"name":"\K[^"]+' \
              | head -1)
            VERSION=$(echo "$TAG" | sed "$TAG_PATTERN")
          elif [[ "${RELEASE_TYPE}" == "any" ]]; then
            TAG=$(curl -s \
              -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
              -H "Accept: application/vnd.github+json" \
              "https://api.github.com/repos/${UPSTREAM_REPO}/releases?per_page=1" \
              | grep '"tag_name"' \
              | head -1 \
              | sed 's/.*"tag_name": "\([^"]*\)".*/\1/')
            VERSION=$(echo "$TAG" | sed "$TAG_PATTERN")
          else
            TAG=$(curl -s \
              -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
              -H "Accept: application/vnd.github+json" \
              "https://api.github.com/repos/${UPSTREAM_REPO}/releases/latest" \
              | grep '"tag_name"' \
              | sed 's/.*"tag_name": "\([^"]*\)".*/\1/')
            VERSION=$(echo "$TAG" | sed "$TAG_PATTERN")
          fi
          if [[ -z "$VERSION" ]]; then
            echo "ERROR: Failed to determine upstream version" >&2
            exit 1
          fi
          if [[ "$VERSION" == "null" ]]; then
            echo "ERROR: No releases found upstream" >&2
            exit 1
          fi
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
```

After:
```yaml
      - name: Get latest upstream version
        id: upstream
        env:
          UPSTREAM_REPO: ${{ matrix.package.upstream }}
          TAG_PATTERN: ${{ matrix.package.tag_pattern }}
          RELEASE_TYPE: ${{ matrix.package.release_type }}
          CHECK_TYPE: ${{ matrix.package.check_type }}
          REDIRECT_URL: ${{ matrix.package.url }}
          FILENAME_PREFIX: ${{ matrix.package.filename_prefix }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python3 .github/scripts/check_version.py
```

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/check_version.py .github/scripts/tests/test_check_version.py .github/workflows/check-updates.yml
git commit -m "feat: extract check_version.py from check-updates workflow"
```

---

### Task 4: push_to_aur.py

**Files:**
- Create: `.github/scripts/push_to_aur.py`
- Create: `.github/scripts/tests/test_push_to_aur.py`
- Modify: `.github/workflows/push-to-aur.yml`

- [ ] **Step 1: Write the failing tests**

Create `.github/scripts/tests/test_push_to_aur.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from push_to_aur import get_changed_packages, read_pkgver_from_srcinfo


def test_get_changed_packages_excludes_archive_and_non_pkgbuild(mocker):
    mock_result = MagicMock()
    mock_result.stdout = "joplin-bin/PKGBUILD\narchive/old-pkg/PKGBUILD\nsome/file.txt\nxmind/PKGBUILD\n"
    mocker.patch("push_to_aur.subprocess.run", return_value=mock_result)
    assert get_changed_packages(Path("/workspace")) == ["joplin-bin", "xmind"]


def test_get_changed_packages_returns_empty_when_no_pkgbuilds(mocker):
    mock_result = MagicMock()
    mock_result.stdout = "README.md\nsome/other.txt\n"
    mocker.patch("push_to_aur.subprocess.run", return_value=mock_result)
    assert get_changed_packages(Path("/workspace")) == []


def test_read_pkgver_from_srcinfo(tmp_path):
    srcinfo = tmp_path / ".SRCINFO"
    srcinfo.write_text("pkgbase = mypkg\n\tpkgver = 3.6.12\n\tpkgrel = 1\n")
    assert read_pkgver_from_srcinfo(srcinfo) == "3.6.12"


def test_read_pkgver_raises_if_not_found(tmp_path):
    srcinfo = tmp_path / ".SRCINFO"
    srcinfo.write_text("pkgbase = mypkg\n\tpkgrel = 1\n")
    with pytest.raises(RuntimeError, match="pkgver not found"):
        read_pkgver_from_srcinfo(srcinfo)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd .github/scripts && pytest tests/test_push_to_aur.py -v
```

Expected: `ImportError: No module named 'push_to_aur'`

- [ ] **Step 3: Write push_to_aur.py**

Create `.github/scripts/push_to_aur.py`:

```python
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_changed_packages(workdir: Path) -> list:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        capture_output=True, text=True, check=True, cwd=workdir,
    )
    packages = []
    for line in result.stdout.splitlines():
        if line.endswith("/PKGBUILD") and not line.startswith("archive/"):
            packages.append(line.removesuffix("/PKGBUILD"))
    return packages


def read_pkgver_from_srcinfo(srcinfo_path: Path) -> str:
    for line in srcinfo_path.read_text().splitlines():
        if line.strip().startswith("pkgver = "):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"pkgver not found in {srcinfo_path}")


def push_package(package: str, workdir: Path, user_name: str, user_email: str) -> None:
    aur_dir = Path(f"/tmp/aur-{package}")
    subprocess.run(
        ["git", "clone", f"ssh://aur@aur.archlinux.org/{package}.git", str(aur_dir)],
        check=True,
    )
    srcinfo = workdir / package / ".SRCINFO"
    if not srcinfo.exists():
        raise RuntimeError(f"{package}/.SRCINFO missing — cannot push to AUR")
    shutil.copy(workdir / package / "PKGBUILD", aur_dir / "PKGBUILD")
    shutil.copy(srcinfo, aur_dir / ".SRCINFO")
    subprocess.run(["git", "config", "user.name", user_name], check=True, cwd=aur_dir)
    subprocess.run(["git", "config", "user.email", user_email], check=True, cwd=aur_dir)
    subprocess.run(["git", "add", "PKGBUILD", ".SRCINFO"], check=True, cwd=aur_dir)
    diff = subprocess.run(["git", "diff", "--quiet", "--cached"], cwd=aur_dir)
    if diff.returncode == 0:
        print(f"No changes for {package}, skipping")
        return
    pkgver = read_pkgver_from_srcinfo(aur_dir / ".SRCINFO")
    subprocess.run(
        ["git", "commit", "-m", f"{package}: update to {pkgver}"],
        check=True, cwd=aur_dir,
    )
    subprocess.run(["git", "push", "origin", "master"], check=True, cwd=aur_dir)


def main() -> None:
    workdir = Path.cwd()
    user_name = os.environ["AUR_USER_NAME"]
    user_email = os.environ["AUR_USER_EMAIL"]
    packages = get_changed_packages(workdir)
    if not packages:
        print("No PKGBUILD changes detected")
        return
    failed = []
    for package in packages:
        print(f"Pushing {package} to AUR...")
        try:
            push_package(package, workdir, user_name, user_email)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            failed.append(package)
    if failed:
        print(f"FAILED packages: {' '.join(failed)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd .github/scripts && pytest tests/test_push_to_aur.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Update push-to-aur.yml — Push changed packages step**

The git identity was hardcoded in the bash; move it to `env:` using the same secrets pattern as `update-pkgbuild.yml`.

In `.github/workflows/push-to-aur.yml`:

Before:
```yaml
      - name: Push changed packages to AUR
        run: |
          set -euo pipefail
          WORKDIR=$(pwd)
          FAILED=()
          CHANGED=$(git diff --name-only HEAD~1 HEAD | grep '/PKGBUILD$' | grep -v '^archive/' | sed 's|/PKGBUILD$||' || true)
          if [[ -z "$CHANGED" ]]; then
            echo "No PKGBUILD changes detected"
            exit 0
          fi
          while IFS= read -r PACKAGE; do
            echo "Pushing ${PACKAGE} to AUR..."
            if ! git clone "ssh://aur@aur.archlinux.org/${PACKAGE}.git" "/tmp/aur-${PACKAGE}"; then
              echo "ERROR: Failed to clone AUR repo for ${PACKAGE}"
              FAILED+=("${PACKAGE}")
              continue
            fi
            if [[ ! -f "${PACKAGE}/.SRCINFO" ]]; then
              echo "ERROR: ${PACKAGE}/.SRCINFO missing — cannot push to AUR"
              FAILED+=("${PACKAGE}")
              continue
            fi
            cp "${PACKAGE}/PKGBUILD" "/tmp/aur-${PACKAGE}/"
            cp "${PACKAGE}/.SRCINFO" "/tmp/aur-${PACKAGE}/"
            cd "/tmp/aur-${PACKAGE}"
            git config user.name "bacteriostat"
            git config user.email "dev.bacteriostat@aleeas.com"
            git add PKGBUILD .SRCINFO
            if git diff --quiet --cached; then
              echo "No changes for ${PACKAGE}, skipping"
              cd "$WORKDIR"
              continue
            fi
            PKGVER=$(grep -m1 'pkgver = ' .SRCINFO | awk '{print $3}')
            git commit -m "${PACKAGE}: update to ${PKGVER}"
            if ! git push origin master; then
              echo "ERROR: Failed to push ${PACKAGE} to AUR"
              FAILED+=("${PACKAGE}")
            fi
            cd "$WORKDIR"
          done <<< "$CHANGED"
          if [[ ${#FAILED[@]} -gt 0 ]]; then
            echo "FAILED packages: ${FAILED[*]}"
            exit 1
          fi
```

After:
```yaml
      - name: Push changed packages to AUR
        env:
          AUR_USER_NAME: ${{ secrets.AUR_USER_NAME }}
          AUR_USER_EMAIL: ${{ secrets.AUR_USER_EMAIL }}
        run: python3 .github/scripts/push_to_aur.py
```

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/push_to_aur.py .github/scripts/tests/test_push_to_aur.py .github/workflows/push-to-aur.yml
git commit -m "feat: extract push_to_aur.py from push-to-aur workflow"
```

---

### Task 5: create_pr.py

**Files:**
- Create: `.github/scripts/create_pr.py`
- Create: `.github/scripts/tests/test_create_pr.py`
- Modify: `.github/workflows/update-pkgbuild.yml`

- [ ] **Step 1: Write the failing tests**

Create `.github/scripts/tests/test_create_pr.py`:

```python
from pathlib import Path

import pytest

from create_pr import branch_name, read_pkgver_from_srcinfo


def test_branch_name():
    assert branch_name("joplin-bin", "3.6.12") == "update/joplin-bin-v3.6.12"


def test_branch_name_with_complex_version():
    assert branch_name("xmind", "26.03.04129.202605111647") == "update/xmind-v26.03.04129.202605111647"


def test_read_pkgver_from_srcinfo(tmp_path):
    srcinfo = tmp_path / ".SRCINFO"
    srcinfo.write_text("pkgbase = joplin-bin\n\tpkgver = 3.6.12\n\tpkgrel = 1\n")
    assert read_pkgver_from_srcinfo(srcinfo) == "3.6.12"


def test_read_pkgver_raises_if_not_found(tmp_path):
    srcinfo = tmp_path / ".SRCINFO"
    srcinfo.write_text("pkgbase = joplin-bin\n\tpkgrel = 1\n")
    with pytest.raises(RuntimeError, match="pkgver not found"):
        read_pkgver_from_srcinfo(srcinfo)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd .github/scripts && pytest tests/test_create_pr.py -v
```

Expected: `ImportError: No module named 'create_pr'`

- [ ] **Step 3: Write create_pr.py**

Create `.github/scripts/create_pr.py`:

```python
import os
import subprocess
import sys
from pathlib import Path


def read_pkgver_from_srcinfo(srcinfo_path: Path) -> str:
    for line in srcinfo_path.read_text().splitlines():
        if line.strip().startswith("pkgver = "):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"pkgver not found in {srcinfo_path}")


def branch_name(package: str, pkgver: str) -> str:
    return f"update/{package}-v{pkgver}"


def main() -> None:
    package = os.environ["PACKAGE"]
    user_name = os.environ["AUR_USER_NAME"]
    user_email = os.environ["AUR_USER_EMAIL"]

    pkgver = read_pkgver_from_srcinfo(Path(package) / ".SRCINFO")
    branch = branch_name(package, pkgver)

    subprocess.run(["git", "config", "user.name", user_name], check=True)
    subprocess.run(["git", "config", "user.email", user_email], check=True)

    result = subprocess.run(["git", "checkout", "-b", branch], capture_output=True)
    if result.returncode != 0:
        subprocess.run(["git", "checkout", branch], check=True)

    subprocess.run(
        ["git", "add", f"{package}/PKGBUILD", f"{package}/.SRCINFO"], check=True
    )

    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode != 0:
        subprocess.run(
            ["git", "commit", "-m", f"{package}: update to {pkgver}"], check=True
        )

    subprocess.run(
        ["git", "push", "origin", branch, "--force-with-lease"], check=True
    )

    existing = subprocess.run(
        [
            "gh", "pr", "list",
            "--head", branch,
            "--state", "open",
            "--json", "number",
            "-q", ".[0].number",
        ],
        capture_output=True,
        text=True,
    )
    if existing.stdout.strip():
        print(f"PR for {branch} already open, skipping creation")
    else:
        subprocess.run(
            [
                "gh", "pr", "create",
                "--title", f"{package}: update to {pkgver}",
                "--body", f"Automated update to upstream release v{pkgver}.",
                "--base", "master",
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd .github/scripts && pytest tests/test_create_pr.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Run the full test suite**

```bash
cd .github/scripts && pytest tests/ -v
```

Expected: `17 passed` (3 + 6 + 4 + 4)

- [ ] **Step 6: Update update-pkgbuild.yml — Create update branch and open PR step**

The `git config` calls and PR logic move into the script. Add `AUR_USER_NAME` and `AUR_USER_EMAIL` to the `env:` block (previously interpolated as `${{ secrets.AUR_USER_NAME }}` directly in bash).

In `.github/workflows/update-pkgbuild.yml`:

Before:
```yaml
      - name: Create update branch and open PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PACKAGE: ${{ inputs.package }}
          VERSION: ${{ inputs.version }}
        run: |
          git config user.name "${{ secrets.AUR_USER_NAME }}"
          git config user.email "${{ secrets.AUR_USER_EMAIL }}"
          PKGVER=$(grep -m1 'pkgver = ' "${PACKAGE}/.SRCINFO" | awk '{print $3}')
          BRANCH="update/${PACKAGE}-v${PKGVER}"
          git checkout -b "${BRANCH}" 2>/dev/null || git checkout "${BRANCH}"
          git add "${PACKAGE}/PKGBUILD" "${PACKAGE}/.SRCINFO"
          if git diff --cached --quiet; then
            echo "Nothing to commit, skipping"
          else
            git commit -m "${PACKAGE}: update to ${PKGVER}"
          fi
          git push origin "${BRANCH}" --force-with-lease
          if gh pr list --head "${BRANCH}" --state open --json number -q '.[0].number' 2>/dev/null | grep -q .; then
            echo "PR for ${BRANCH} already open, skipping creation"
          else
            gh pr create \
              --title "${PACKAGE}: update to ${PKGVER}" \
              --body "Automated update to upstream release v${PKGVER}." \
              --base master
          fi
```

After:
```yaml
      - name: Create update branch and open PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PACKAGE: ${{ inputs.package }}
          VERSION: ${{ inputs.version }}
          AUR_USER_NAME: ${{ secrets.AUR_USER_NAME }}
          AUR_USER_EMAIL: ${{ secrets.AUR_USER_EMAIL }}
        run: python3 .github/scripts/create_pr.py
```

- [ ] **Step 7: Commit**

```bash
git add .github/scripts/create_pr.py .github/scripts/tests/test_create_pr.py .github/workflows/update-pkgbuild.yml
git commit -m "feat: extract create_pr.py from update-pkgbuild workflow"
```
