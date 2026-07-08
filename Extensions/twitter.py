import html
import re

import emoji
import requests

OEMBED_URL = "https://publish.twitter.com/oembed"


class TweetFetchError(RuntimeError):
    """Raised when a post's text can't be fetched via the public oEmbed API."""


def _strip_emojis(text):
    if hasattr(emoji, "replace_emoji"):
        return emoji.replace_emoji(text, replace="")

    get_emoji_regexp = getattr(emoji, "get_emoji_regexp", None)
    if get_emoji_regexp:
        return get_emoji_regexp().sub("", text)

    return text


def get_text(url):
    """Fetch a tweet/post's text via X/Twitter's public oEmbed endpoint.

    No API keys, developer account, or login required - this is the same
    unauthenticated endpoint browsers use to render embedded tweets, so it
    works for any public post's URL.
    """
    try:
        response = requests.get(OEMBED_URL, params={"url": url}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        raise TweetFetchError(f"Could not reach X/Twitter: {error}")

    html_fragment = response.json().get("html", "")
    match = re.search(r"<p[^>]*>(.*?)</p>", html_fragment, re.DOTALL)
    if not match:
        raise TweetFetchError("This post could not be read (it may be private, deleted, or age-restricted).")

    text = re.sub(r"<[^>]+>", " ", match.group(1))
    text = html.unescape(text).strip()
    return _strip_emojis(text)
