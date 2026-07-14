"""Tokenizer support: bundled vocab must work with no network access."""

from __future__ import annotations

import pytest

from soon_format import encode, stats
from soon_format.tokencost import _BUNDLED, get_encoder, text_cost

tiktoken = pytest.importorskip("tiktoken")


def test_bundled_encoding_registered():
    assert "o200k_base" in _BUNDLED


def test_offline_matches_upstream():
    """Bundled encoder must produce identical token ids to tiktoken.get_encoding."""
    offline = get_encoder("o200k_base")
    online = tiktoken.get_encoding("o200k_base")
    for sample in [
        "",
        "Hello, world!",
        '{"users":[{"id":1,"name":"Ada"}]}',
        "🌟 emoji test 🔥",
        "multi\nline\ntext with\ttabs",
        "SHAPE hikes = {id,name,km,sunny}\n(1,Blue Lake Trail,7.5,true)",
    ]:
        assert offline.encode(sample) == online.encode(sample), sample


def test_encoder_cached():
    a = get_encoder("o200k_base")
    b = get_encoder("o200k_base")
    assert a is b


def test_get_encoder_none_returns_none():
    assert get_encoder(None) is None


def test_text_cost_falls_back_to_chars_when_no_encoder():
    assert text_cost("hello", None) == 5


def test_offline_without_tiktoken_cache(monkeypatch, tmp_path):
    """Bundled vocab must load even with network fully blocked and no cache.

    Points TIKTOKEN_CACHE_DIR at an empty directory and sets bogus proxies so
    any network fetch fails immediately. If the encoder still loads, we know
    the bundled vocab is doing the work.
    """
    empty_cache = tmp_path / "cache"
    empty_cache.mkdir()
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(empty_cache))
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    # Force a fresh build (bypass the module-level cache).
    from soon_format import tokencost

    monkeypatch.setattr(tokencost, "_CACHE", {})
    enc = tokencost.get_encoder("o200k_base")
    assert enc is not None
    assert enc.encode("hello world")
    # Empty cache dir confirms nothing was written locally either.
    assert not any(empty_cache.iterdir())


def test_stats_reports_tokens_when_tokenizer_set():
    data = {"users": [{"id": i, "name": f"user{i}"} for i in range(10)]}
    report = stats(data, tokenizer="o200k_base")
    assert "json_tokens" in report
    assert "soon_tokens" in report
    assert report["json_tokens"] > 0
    assert report["soon_tokens"] > 0
    # SOON should be at least not-worse in tokens (never-worse guarantee).
    assert report["soon_tokens"] <= report["json_tokens"]


def test_encode_with_tokenizer_offline():
    """End-to-end: encode() with tokenizer works and round-trips."""
    from soon_format import decode

    data = {"items": [{"id": i, "label": f"n{i}"} for i in range(4)]}
    doc = encode(data, tokenizer="o200k_base")
    assert decode(doc) == data


def test_unknown_bundled_falls_through_to_tiktoken():
    """A non-bundled name still resolves via tiktoken.get_encoding.

    Only asserts the branch is taken — the encoding itself may need network
    on a fresh box, which is the whole point of bundling the ones we care
    about. Skip when the cl100k_base file isn't already cached locally.
    """
    if "cl100k_base" in _BUNDLED:
        pytest.skip("cl100k_base is bundled; this test targets the fallback branch")
    try:
        enc = get_encoder("cl100k_base")
    except Exception:  # pragma: no cover — network offline on the test box
        pytest.skip("cl100k_base unavailable offline (expected)")
    assert enc is not None
