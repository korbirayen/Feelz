from Extensions import history_store


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(history_store, "DB_PATH", tmp_path / "history.db")


def test_log_and_get_recent_roundtrip(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    history_store.log_entry(mode="depression", text="feeling okay today", result="not depressive", confidence=0.8)

    timestamp, mode, result, confidence, excerpt, signal = history_store.get_recent(5)[0]
    assert mode == "depression"
    assert result == "not depressive"
    assert confidence == 0.8
    assert signal == 0.8
    assert excerpt == "feeling okay today"


def test_signal_is_negative_for_depressive_result(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    history_store.log_entry(mode="depression", text="...", result="depressive", confidence=0.9)
    signal = history_store.get_recent(1)[0][-1]
    assert signal == -0.9


def test_signal_for_polarity_modes():
    assert history_store._signal("polarity", "positive", 0.7) == 0.7
    assert history_store._signal("polarity", "negative", 0.7) == -0.7
    assert history_store._signal("polarity", "neutral", 0.7) == 0.0


def test_clear_removes_all_entries(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    history_store.log_entry(mode="polarity", text="hi", result="positive", confidence=0.5)
    history_store.clear()
    assert history_store.get_recent(10) == []


def test_get_trend_is_chronological(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    history_store.log_entry(mode="polarity", text="a", result="positive", confidence=0.6)
    history_store.log_entry(mode="polarity", text="b", result="negative", confidence=0.4)

    trend = history_store.get_trend()
    assert len(trend) == 2
    assert trend[0][1] == 0.6
    assert trend[1][1] == -0.4
