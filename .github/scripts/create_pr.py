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
