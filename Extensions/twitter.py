import os

from twython import Twython
import emoji


def _build_client():
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise RuntimeError(
            "Set TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET before using Twitter lookups."
        )

    return Twython(
        consumer_key,
        consumer_secret,
        access_token,
        access_token_secret,
    )


def _count_emojis(text):
    if hasattr(emoji, "emoji_list"):
        return len(emoji.emoji_list(text))

    unicode_emoji = getattr(emoji, "UNICODE_EMOJI", {})
    return sum(text.count(symbol) for symbol in unicode_emoji)


def _remove_emojis(text):
    if hasattr(emoji, "replace_emoji"):
        return emoji.replace_emoji(text, replace="")

    get_emoji_regexp = getattr(emoji, "get_emoji_regexp", None)
    if get_emoji_regexp:
        return get_emoji_regexp().sub(u"", text)

    return text

def get_text(url):
    #url = 'https://twitter.com/VictorIsrael_/status/1348272317663731713?s=20'
    i_d = url.split('/')[-1] # Return the last string after '/'
    num = i_d.split('?')[0] # Return the ID before '?' 
    # The show status function from twython accepts the tweet ID
    t = _build_client()
    tweet = t.show_status(id=int(num),tweet_mode='extended')
    text = tweet['full_text']

    emoji_count = _count_emojis(text)
    
    if emoji_count == 0: # If there is no emoji
        return (text) # Return the text from status
    else:
        return _remove_emojis(text) # Return the text without emojis