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
