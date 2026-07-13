import pytest
import requests

from Extensions import twitter


class _FakeResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json


def test_get_text_extracts_paragraph_and_strips_emoji(monkeypatch):
    html_fragment = (
        '<blockquote class="twitter-tweet"><p lang="en" dir="ltr">'
        "Hello world! \U0001F389</p>&mdash; Someone</blockquote>"
    )
    monkeypatch.setattr(twitter.requests, "get", lambda *a, **k: _FakeResponse({"html": html_fragment}))
    text = twitter.get_text("https://x.com/user/status/12345")
    assert "Hello world!" in text
    assert "\U0001F389" not in text


def test_get_text_raises_on_missing_paragraph(monkeypatch):
    monkeypatch.setattr(twitter.requests, "get", lambda *a, **k: _FakeResponse({"html": "<div>no paragraph here</div>"}))
    with pytest.raises(twitter.TweetFetchError):
        twitter.get_text("https://x.com/user/status/12345")


def test_get_text_raises_on_network_error(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(twitter.requests, "get", boom)
    with pytest.raises(twitter.TweetFetchError):
        twitter.get_text("https://x.com/user/status/12345")


def test_get_text_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(twitter.requests, "get", lambda *a, **k: _FakeResponse({}, status=404))
    with pytest.raises(twitter.TweetFetchError):
        twitter.get_text("https://x.com/user/status/12345")
