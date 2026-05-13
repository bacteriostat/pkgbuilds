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
