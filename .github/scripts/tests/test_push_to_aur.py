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
