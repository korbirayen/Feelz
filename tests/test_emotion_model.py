import pytest

from Extensions import emotion_model


def test_is_available_reflects_whether_transformers_imports():
    # Whatever this environment actually has installed, is_available() should
    # agree with a direct import attempt rather than raising.
    try:
        import transformers  # noqa: F401
        expected = True
    except ImportError:
        expected = False
    assert emotion_model.is_available() is expected


def test_score_emotions_raises_a_clear_error_when_the_pipeline_cant_load(monkeypatch):
    """Simulates any failure building the underlying transformers pipeline -
    missing package, incompatible torch/torchvision, blocked model download,
    etc. - and checks it degrades to one clear, catchable error type instead
    of an arbitrary exception leaking out of this optional feature."""
    monkeypatch.setattr(emotion_model, "_pipeline_cache", None)

    def boom():
        raise RuntimeError("simulated: incompatible torch/torchvision build")

    monkeypatch.setattr(emotion_model, "_build_pipeline", boom)

    with pytest.raises(emotion_model.EmotionModelUnavailable):
        emotion_model.score_emotions("anything")
