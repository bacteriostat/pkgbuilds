# Liberica JDK automated update support

**Date:** 2026-05-15

## Goal

Add all four Liberica JDK packages to the automated version-checking pipeline. The upstream repo (`bell-sw/Liberica`) publishes releases for every JDK major version in a single GitHub repository, so a per-package tag prefix filter is needed to find the right latest release for each package.

## Packages in scope

| Package | Java major | Tag prefix |
|---|---|---|
| `liberica-jdk-11-bin` | 11 | `11.` |
| `liberica-jdk-11-full-bin` | 11 | `11.` |
| `liberica-jdk-11-lite-bin` | 11 | `11.` |
| `liberica-jdk-17-full-bin` | 17 | `17.` |

## Part 1 — PKGBUILD unification

`liberica-jdk-11-full-bin` and `liberica-jdk-17-full-bin` currently use a dual-variable scheme:

- `pkgver=11.0.31.u11` — AUR display format (`.u` instead of `+`)
- `_pkgver=11.0.31+11` — used in download URLs

`liberica-jdk-11-bin` and `liberica-jdk-11-lite-bin` already use a single `pkgver=11.0.31+11` (with `+`), which is valid in PKGBUILD. The dual-variable scheme must be unified before automation can work, because `update-pkgbuild.yml` performs a single `sed` substitution on one variable and cannot keep both in sync.

**Changes to `liberica-jdk-11-full-bin/PKGBUILD` and `liberica-jdk-17-full-bin/PKGBUILD`:**
- Remove the `_pkgver` variable
- Change `pkgver=X.uY` → `pkgver=X+Y`
- Replace all `$_pkgver` / `${_pkgver...}` references with `$pkgver` / `${pkgver...}` in `source_*` arrays and the `package()` function

Update both `.SRCINFO` files in the same commit so the `pkgver` line reflects the new format.

## Part 2 — `tag_prefix` filtering in `check_version.py`

The GitHub Releases API returns all releases in reverse chronological order regardless of JDK major version. A `tag_prefix` parameter is added to filter for the right major version.

**`fetch_github_version` signature change:**

```python
def fetch_github_version(
    upstream_repo: str,
    tag_pattern: str,
    release_type: str,
    token: str,
    tag_prefix: str = "",
) -> str:
```

When `tag_prefix` is non-empty, the function fetches pages of up to 100 releases and returns the `tag_name` of the first release whose tag starts with `tag_prefix`. A safety cap of 10 pages (1000 releases) prevents infinite loops. If no matching release is found, a `RuntimeError` is raised (consistent with existing error handling).

When `tag_prefix` is empty, behaviour is identical to today.

## Part 3 — Config and workflow wiring

**`packages.yml`** — four new entries:

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

No `tag_pattern` is needed — Liberica tags have no `v` prefix, so the default `s/^v//` is a no-op and the raw tag (e.g. `11.0.31+11`) matches `pkgver` directly.

**`parse_packages.py`** — no changes needed; the `tag_prefix` field passes through the YAML serialisation automatically.

**`check-updates.yml`** — add `TAG_PREFIX: ${{ matrix.package.tag_prefix }}` to the env block of the "Get latest upstream version" step.

**`check_version.py`** — read `TAG_PREFIX` from the environment and pass it to `fetch_github_version`.

## Error handling

- **No matching release found**: `fetch_github_version` raises `RuntimeError`; the matrix job for that package fails; other packages are unaffected (`fail-fast: false`).
- **No `tag_prefix` set**: existing code path is unchanged.

## What is not changing

- `update-pkgbuild.yml` — no changes; it already updates `pkgver` via `sed` and regenerates `.SRCINFO` in an Arch container
- `push-to-aur.yml` — no changes
- `create_pr.py` / `push_to_aur.py` / `parse_packages.py` — no changes
