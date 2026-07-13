from Extensions import PolarityScore


def test_sentiment_returns_vader_keys():
    scores = PolarityScore.sentiment("I love this, it's wonderful!")
    assert set(scores) == {"neg", "neu", "pos", "compound"}


def test_sentiment_positive_text_scores_higher_positive():
    scores = PolarityScore.sentiment("This is amazing and wonderful, I'm so happy!")
    assert scores["pos"] > scores["neg"]


def test_sentiment_negative_text_scores_higher_negative():
    scores = PolarityScore.sentiment("This is terrible and awful, I hate it.")
    assert scores["neg"] > scores["pos"]
