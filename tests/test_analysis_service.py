from Extensions import analysis_service


def test_score_polarity_has_the_three_expected_buckets():
    scores = analysis_service.score_polarity("I am happy and grateful today")
    assert set(scores) == {"negative", "neutral", "positive"}
    # Three independent VADER fractions rounded to ints won't always sum to
    # exactly 100 - just check they're in the right ballpark.
    assert 95 <= sum(scores.values()) <= 105


def test_score_depression_low_confidence_flag_matches_threshold():
    result = analysis_service.score_depression("ok")
    assert isinstance(result.is_depressive, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert result.low_confidence == (result.confidence < analysis_service.LOW_CONFIDENCE_THRESHOLD)


def test_show_crisis_resources_requires_depressive_and_high_confidence():
    result = analysis_service.score_depression("I feel hopeless, empty, and exhausted all the time")
    expected = result.is_depressive and result.confidence >= analysis_service.CRISIS_CONFIDENCE_THRESHOLD
    assert result.show_crisis_resources == expected


def test_is_connected_true_when_socket_connects(monkeypatch):
    monkeypatch.setattr(analysis_service.socket, "create_connection", lambda *a, **k: None)
    assert analysis_service.is_connected() is True


def test_is_connected_false_when_socket_raises(monkeypatch):
    def raise_oserror(*args, **kwargs):
        raise OSError("no network")

    monkeypatch.setattr(analysis_service.socket, "create_connection", raise_oserror)
    assert analysis_service.is_connected() is False
