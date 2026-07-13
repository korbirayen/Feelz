import pandas as pd

from Extensions import DepressionScore


def test_tokenize_unigrams_lowercases_removes_stopwords_and_stems():
    tokens = DepressionScore.tokenize_unigrams("The Runners are running quickly")
    assert "the" not in tokens
    assert "are" not in tokens
    assert any(token.startswith("run") for token in tokens)


def test_process_message_default_gram_returns_raw_bigrams():
    # Documents the V1 tokenizer bug tokenize_unigrams works around: gram=2
    # (the default) returns early, before stopword removal/stemming ever run.
    # Words of length <= 2 ("I", "am") are dropped first, so bigrams are
    # built from the remaining words only.
    tokens = DepressionScore.process_message("Running quickly outside")
    assert tokens == ["running quickly", "quickly outside"]


def test_build_pipeline_fits_and_predicts():
    pipeline = DepressionScore.build_pipeline()
    messages = [
        "I am so happy and excited about life",
        "Everything is wonderful today",
        "I feel hopeless and empty, nothing matters anymore",
        "Extreme sadness and lack of energy every day",
    ] * 5
    labels = [0, 0, 1, 1] * 5
    pipeline.fit(pd.Series(messages), pd.Series(labels))
    prediction = pipeline.predict(["I feel hopeless and empty"])
    assert prediction[0] in (0, 1)


def test_predict_depressive_with_confidence_uses_shipped_pipeline():
    is_depressive, confidence = DepressionScore.predict_depressive_with_confidence(
        "I feel hopeless, empty, and exhausted all the time"
    )
    assert isinstance(is_depressive, bool)
    assert 0.0 <= confidence <= 1.0


def test_predict_depressive_agrees_with_confidence_variant():
    text = "I am so happy and love my life"
    label = DepressionScore.predict_depressive(text)
    is_depressive, _ = DepressionScore.predict_depressive_with_confidence(text)
    assert label == is_depressive
