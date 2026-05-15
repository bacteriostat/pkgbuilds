import json
import os

import yaml


def load_packages(config_path: str) -> list:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    pkgs = [
        p for p in config["packages"]
        if p.get("check_type") in ("github", "gitlab", "xmind_custom", "liberica")
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
