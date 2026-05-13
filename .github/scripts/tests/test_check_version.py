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
