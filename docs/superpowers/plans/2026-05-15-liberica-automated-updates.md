# Liberica Automated Updates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all four Liberica JDK packages to the automated version-checking pipeline, using a new `tag_prefix` field to filter releases from the shared `bell-sw/Liberica` GitHub repo.

**Architecture:** Unify the two "full" packages to use a single `pkgver=X+Y` variable (matching the two existing packages), then extend `check_version.py` with paginated tag-prefix filtering and wire the new `TAG_PREFIX` env var through `check-updates.yml` and `packages.yml`.

**Tech Stack:** Python 3, GitHub Releases API, Bash/PKGBUILD, GitHub Actions YAML

---

## File map

| File | Change |
|---|---|
| `liberica-jdk-11-full-bin/PKGBUILD` | Remove `_pkgver`, unify to `pkgver=11.0.31+11` |
| `liberica-jdk-11-full-bin/.SRCINFO` | Update `pkgver` and `provides` lines |
| `liberica-jdk-17-full-bin/PKGBUILD` | Remove `_pkgver`, unify to `pkgver=17.0.19+11` |
| `liberica-jdk-17-full-bin/.SRCINFO` | Update `pkgver` and `provides` lines |
| `.github/scripts/check_version.py` | Add `tag_prefix` pagination to `fetch_github_version` |
| `.github/workflows/check-updates.yml` | Add `TAG_PREFIX` env var to version-check step |
| `.github/packages.yml` | Add four Liberica entries |

---

### Task 1: Unify liberica-jdk-11-full-bin PKGBUILD

**Files:**
- Modify: `liberica-jdk-11-full-bin/PKGBUILD`
- Modify: `liberica-jdk-11-full-bin/.SRCINFO`

- [ ] **Step 1: Replace the dual pkgver variables with a single one**

In `liberica-jdk-11-full-bin/PKGBUILD`, replace:
```
pkgver=11.0.31.u11
_pkgver=11.0.31+11
```
with:
```
pkgver=11.0.31+11
```

- [ ] **Step 2: Update source arrays to use `$pkgver`**

In `liberica-jdk-11-full-bin/PKGBUILD`, replace:
```
source_aarch64=(https://download.bell-sw.com/java/$_pkgver/bellsoft-jdk$_pkgver-linux-aarch64-full.tar.gz)
source_armv7h=(https://download.bell-sw.com/java/$_pkgver/bellsoft-jdk$_pkgver-linux-arm32-vfp-hflt-full.tar.gz)
source_armv8h=(${source_armv7h[@]})
source_x86_64=(https://download.bell-sw.com/java/$_pkgver/bellsoft-jdk$_pkgver-linux-amd64-full.tar.gz)
```
with:
```
source_aarch64=(https://download.bell-sw.com/java/$pkgver/bellsoft-jdk$pkgver-linux-aarch64-full.tar.gz)
source_armv7h=(https://download.bell-sw.com/java/$pkgver/bellsoft-jdk$pkgver-linux-arm32-vfp-hflt-full.tar.gz)
source_armv8h=(${source_armv7h[@]})
source_x86_64=(https://download.bell-sw.com/java/$pkgver/bellsoft-jdk$pkgver-linux-amd64-full.tar.gz)
```

- [ ] **Step 3: Update package() to use `$pkgver`**

In `liberica-jdk-11-full-bin/PKGBUILD`, replace:
```
  cd jdk-${_pkgver/+*/}-full
```
with:
```
  cd jdk-${pkgver/+*/}-full
```

- [ ] **Step 4: Update .SRCINFO pkgver line**

In `liberica-jdk-11-full-bin/.SRCINFO`, replace:
```
	pkgver = 11.0.31.u11
```
with:
```
	pkgver = 11.0.31+11
```

- [ ] **Step 5: Update .SRCINFO provides lines**

In `liberica-jdk-11-full-bin/.SRCINFO`, replace:
```
	provides = liberica-jdk-11-bin=11.0.31.u11
	provides = liberica-jdk-11-lite-bin=11.0.31.u11
	provides = liberica-jre-11-bin=11.0.31.u11
	provides = liberica-jre-11-full-bin=11.0.31.u11
```
with:
```
	provides = liberica-jdk-11-bin=11.0.31+11
	provides = liberica-jdk-11-lite-bin=11.0.31+11
	provides = liberica-jre-11-bin=11.0.31+11
	provides = liberica-jre-11-full-bin=11.0.31+11
```

- [ ] **Step 6: Commit**

```bash
git add liberica-jdk-11-full-bin/PKGBUILD liberica-jdk-11-full-bin/.SRCINFO
git commit -m "liberica-jdk-11-full-bin: unify pkgver to X+Y format"
```

---

### Task 2: Unify liberica-jdk-17-full-bin PKGBUILD

**Files:**
- Modify: `liberica-jdk-17-full-bin/PKGBUILD`
- Modify: `liberica-jdk-17-full-bin/.SRCINFO`

- [ ] **Step 1: Replace the dual pkgver variables with a single one**

In `liberica-jdk-17-full-bin/PKGBUILD`, replace:
```
pkgver=${_java_ver}.0.19.u11
_pkgver=${_java_ver}.0.19+11
```
with:
```
pkgver=17.0.19+11
```

- [ ] **Step 2: Update source arrays to use `$pkgver`**

In `liberica-jdk-17-full-bin/PKGBUILD`, replace:
```
source_aarch64=(https://download.bell-sw.com/java/$_pkgver/bellsoft-jdk$_pkgver-linux-aarch64-full.tar.gz)
source_armv7h=(https://download.bell-sw.com/java/$_pkgver/bellsoft-jdk$_pkgver-linux-arm32-vfp-hflt-full.tar.gz)
source_armv8h=(${source_armv7h[@]})
source_x86_64=(https://download.bell-sw.com/java/$_pkgver/bellsoft-jdk$_pkgver-linux-amd64-full.tar.gz)
```
with:
```
source_aarch64=(https://download.bell-sw.com/java/$pkgver/bellsoft-jdk$pkgver-linux-aarch64-full.tar.gz)
source_armv7h=(https://download.bell-sw.com/java/$pkgver/bellsoft-jdk$pkgver-linux-arm32-vfp-hflt-full.tar.gz)
source_armv8h=(${source_armv7h[@]})
source_x86_64=(https://download.bell-sw.com/java/$pkgver/bellsoft-jdk$pkgver-linux-amd64-full.tar.gz)
```

- [ ] **Step 3: Update package() to use `$pkgver`**

In `liberica-jdk-17-full-bin/PKGBUILD`, replace:
```
  cd jdk-${_pkgver/+*}-full
```
with:
```
  cd jdk-${pkgver/+*}-full
```

- [ ] **Step 4: Update .SRCINFO pkgver line**

In `liberica-jdk-17-full-bin/.SRCINFO`, replace:
```
	pkgver = 17.0.19.u11
```
with:
```
	pkgver = 17.0.19+11
```

- [ ] **Step 5: Update .SRCINFO provides lines**

In `liberica-jdk-17-full-bin/.SRCINFO`, replace:
```
	provides = liberica-jdk-17-bin=17.0.19.u11
	provides = liberica-jdk-17-lite-bin=17.0.19.u11
	provides = liberica-jre-17-bin=17.0.19.u11
	provides = liberica-jre-17-full-bin=17.0.19.u11
	provides = liberica-jdk-17-full-bin=17.0.19.u11
```
with:
```
	provides = liberica-jdk-17-bin=17.0.19+11
	provides = liberica-jdk-17-lite-bin=17.0.19+11
	provides = liberica-jre-17-bin=17.0.19+11
	provides = liberica-jre-17-full-bin=17.0.19+11
	provides = liberica-jdk-17-full-bin=17.0.19+11
```

- [ ] **Step 6: Commit**

```bash
git add liberica-jdk-17-full-bin/PKGBUILD liberica-jdk-17-full-bin/.SRCINFO
git commit -m "liberica-jdk-17-full-bin: unify pkgver to X+Y format"
```

---

### Task 3: Add tag_prefix filtering to check_version.py

**Files:**
- Modify: `.github/scripts/check_version.py`

No tests — per project convention, `.github/scripts/` has no unit tests.

- [ ] **Step 1: Update fetch_github_version signature and add prefix-filtering branch**

In `.github/scripts/check_version.py`, replace the entire `fetch_github_version` function:

```python
def fetch_github_version(
    upstream_repo: str, tag_pattern: str, release_type: str, token: str, tag_prefix: str = ""
) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    if tag_prefix:
        for page in range(1, 11):
            url = f"https://api.github.com/repos/{upstream_repo}/releases?per_page=100&page={page}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as r:
                data = json.loads(r.read())
            if not data:
                break
            for release in data:
                tag = release["tag_name"]
                if tag and tag.startswith(tag_prefix):
                    return apply_tag_pattern(tag, tag_pattern)
        raise RuntimeError(f"No release with tag prefix '{tag_prefix}' found in {upstream_repo}")
    if release_type == "any":
        url = f"https://api.github.com/repos/{upstream_repo}/releases?per_page=1"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        tag = data[0]["tag_name"]
        if tag is None:
            raise RuntimeError("No releases found upstream (tag_name is null)")
    else:
        url = f"https://api.github.com/repos/{upstream_repo}/releases/latest"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        tag = data["tag_name"]
        if tag is None:
            raise RuntimeError("No releases found upstream (tag_name is null)")
    return apply_tag_pattern(tag, tag_pattern)
```

- [ ] **Step 2: Read TAG_PREFIX in main() and pass it through**

In `.github/scripts/check_version.py`, replace the `main` function:

```python
def main() -> None:
    check_type = os.environ["CHECK_TYPE"]
    tag_pattern = os.environ.get("TAG_PATTERN", "s/^v//")
    tag_prefix = os.environ.get("TAG_PREFIX", "")

    try:
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
                tag_prefix,
            )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not version:
        print("ERROR: Failed to determine upstream version", file=sys.stderr)
        sys.exit(1)

    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"version={version}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/check_version.py
git commit -m "feat: add tag_prefix filtering to check_version.py"
```

---

### Task 4: Wire TAG_PREFIX through check-updates.yml

**Files:**
- Modify: `.github/workflows/check-updates.yml`

- [ ] **Step 1: Add TAG_PREFIX to the env block of the version-check step**

In `.github/workflows/check-updates.yml`, replace the env block of the "Get latest upstream version" step:

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
          TAG_PREFIX: ${{ matrix.package.tag_prefix }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python3 .github/scripts/check_version.py
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/check-updates.yml
git commit -m "feat: pass TAG_PREFIX env var to check_version.py"
```

---

### Task 5: Add Liberica entries to packages.yml

**Files:**
- Modify: `.github/packages.yml`

- [ ] **Step 1: Append the four Liberica entries**

In `.github/packages.yml`, append to the `packages:` list:

```yaml
  - name: liberica-jdk-11-bin
    check_type: github
    upstream: bell-sw/Liberica
    tag_prefix: "11."
    release_type: any
  - name: liberica-jdk-11-full-bin
    check_type: github
    upstream: bell-sw/Liberica
    tag_prefix: "11."
    release_type: any
  - name: liberica-jdk-11-lite-bin
    check_type: github
    upstream: bell-sw/Liberica
    tag_prefix: "11."
    release_type: any
  - name: liberica-jdk-17-full-bin
    check_type: github
    upstream: bell-sw/Liberica
    tag_prefix: "17."
    release_type: any
```

- [ ] **Step 2: Commit**

```bash
git add .github/packages.yml
git commit -m "feat: add Liberica JDK packages to automated update checks"
```
