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
