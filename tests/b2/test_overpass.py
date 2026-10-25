"""Unit tests for Overpass retry, endpoint resolution, and OSMnx configuration in b2lib.py.
All network requests are mocked; no live network access occurs.
"""
from unittest.mock import MagicMock, call

import pytest
import requests

import b2lib


# ---------------- Endpoint resolution
def test_resolve_endpoint_precedence(monkeypatch):
    # 1. Explicit argument takes precedence
    monkeypatch.setenv("OVERPASS_URL", "https://env-mirror/api/interpreter")
    assert b2lib.resolve_overpass_endpoint("https://custom-mirror/api/interpreter") == "https://custom-mirror/api/interpreter"

    # 2. Env var takes precedence over default
    assert b2lib.resolve_overpass_endpoint() == "https://env-mirror/api/interpreter"

    # 3. Default fallback when no arg and no env var
    monkeypatch.delenv("OVERPASS_URL", raising=False)
    assert b2lib.resolve_overpass_endpoint() == b2lib.DEFAULT_OVERPASS_URL


def test_overpass_post_appends_interpreter_if_api():
    mock_resp = MagicMock(status_code=200)
    mock_resp.raise_for_status.return_value = None

    with pytest.MonkeyPatch.context() as mp:
        mock_post = MagicMock(return_value=mock_resp)
        mp.setattr(requests, "post", mock_post)

        b2lib.overpass_post("[out:json];", endpoint="https://mirror.example.com/api")
        assert mock_post.call_args[0][0] == "https://mirror.example.com/api/interpreter"


# ---------------- Retries and backoff
def test_overpass_post_success_first_attempt(monkeypatch):
    mock_resp = MagicMock(status_code=200)
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"elements": []}

    mock_post = MagicMock(return_value=mock_resp)
    monkeypatch.setattr(requests, "post", mock_post)

    resp = b2lib.overpass_post("test-query", endpoint="https://overpass-api.de/api/interpreter")
    assert resp.status_code == 200
    assert resp.json() == {"elements": []}
    assert mock_post.call_count == 1
    assert mock_post.call_args[1]["timeout"] == (15, 120)
    assert mock_post.call_args[1]["data"] == {"data": "test-query"}


def test_overpass_post_retries_on_429_then_succeeds(monkeypatch):
    resp_429 = MagicMock(status_code=429)
    resp_200 = MagicMock(status_code=200)
    resp_200.raise_for_status.return_value = None

    mock_post = MagicMock(side_effect=[resp_429, resp_200])
    mock_sleep = MagicMock()
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr("time.sleep", mock_sleep)

    resp = b2lib.overpass_post("query", initial_delay=1.0, backoff_factor=2.0)
    assert resp.status_code == 200
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(1.0)


def test_overpass_post_retries_on_504_then_succeeds(monkeypatch):
    resp_504 = MagicMock(status_code=504)
    resp_200 = MagicMock(status_code=200)
    resp_200.raise_for_status.return_value = None

    mock_post = MagicMock(side_effect=[resp_504, resp_200])
    mock_sleep = MagicMock()
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr("time.sleep", mock_sleep)

    resp = b2lib.overpass_post("query", initial_delay=0.5, backoff_factor=3.0)
    assert resp.status_code == 200
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


def test_overpass_post_retries_on_connect_timeout_with_exponential_backoff(monkeypatch):
    resp_200 = MagicMock(status_code=200)
    resp_200.raise_for_status.return_value = None

    mock_post = MagicMock(side_effect=[
        requests.exceptions.ConnectTimeout("connection timed out"),
        requests.exceptions.ConnectTimeout("connection timed out"),
        resp_200,
    ])
    mock_sleep = MagicMock()
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr("time.sleep", mock_sleep)

    resp = b2lib.overpass_post("query", retries=3, initial_delay=1.0, backoff_factor=2.0)
    assert resp.status_code == 200
    assert mock_post.call_count == 3
    assert mock_sleep.call_args_list == [call(1.0), call(2.0)]


def test_overpass_post_exhaust_retries_raises(monkeypatch):
    mock_post = MagicMock(side_effect=requests.exceptions.ConnectTimeout("timed out"))
    mock_sleep = MagicMock()
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr("time.sleep", mock_sleep)

    with pytest.raises(requests.exceptions.ConnectTimeout):
        b2lib.overpass_post("query", retries=3, initial_delay=1.0, backoff_factor=2.0)

    assert mock_post.call_count == 3
    assert mock_sleep.call_count == 2


def test_overpass_post_non_retryable_http_error_fails_immediately(monkeypatch):
    resp_400 = MagicMock(status_code=400)
    resp_400.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Bad Request", response=resp_400)

    mock_post = MagicMock(return_value=resp_400)
    mock_sleep = MagicMock()
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr("time.sleep", mock_sleep)

    with pytest.raises(requests.exceptions.HTTPError):
        b2lib.overpass_post("bad-syntax-query", retries=3)

    assert mock_post.call_count == 1
    mock_sleep.assert_not_called()


# ---------------- configure_osmnx
def test_configure_osmnx_strips_interpreter_and_sets_timeout():
    import osmnx as ox

    b2lib.configure_osmnx(endpoint="https://overpass.kumi.systems/api/interpreter", timeout=250)
    assert ox.settings.overpass_url == "https://overpass.kumi.systems/api"
    assert ox.settings.requests_timeout == 250

    b2lib.configure_osmnx(endpoint="https://overpass.kumi.systems/api", timeout=300)
    assert ox.settings.overpass_url == "https://overpass.kumi.systems/api"
    assert ox.settings.requests_timeout == 300


# ---------------- classify_overpass_error
def test_classify_overpass_error_network_blocked():
    err = requests.exceptions.ConnectTimeout("HTTPSConnectionPool: Max retries exceeded (ConnectTimeoutError)")
    msg = b2lib.classify_overpass_error(err, endpoint="https://overpass-api.de/api/interpreter")
    assert "NETWORK BLOCKED" in msg
    assert "--endpoint" in msg
    assert "overpass.kumi.systems" in msg


def test_classify_overpass_error_server_busy():
    err = requests.exceptions.ReadTimeout("Read timed out")
    msg = b2lib.classify_overpass_error(err, endpoint="https://overpass-api.de/api/interpreter")
    assert "SERVER BUSY" in msg

    resp_429 = MagicMock(status_code=429)
    err_429 = requests.exceptions.HTTPError("429 Client Error", response=resp_429)
    msg_429 = b2lib.classify_overpass_error(err_429)
    assert "SERVER BUSY" in msg_429
