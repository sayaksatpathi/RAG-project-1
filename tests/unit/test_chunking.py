import pytest

from ragbench.ingestion.chunking import chunk_id, chunk_text, content_hash


def test_basic_windows_with_overlap():
    words = " ".join(str(i) for i in range(10))
    chunks = chunk_text(words, chunk_size=4, overlap=1)
    # step = 3 -> starts 0,3,6,9
    assert chunks[0] == "0 1 2 3"
    assert chunks[1] == "3 4 5 6"
    assert chunks[-1].split()[-1] == "9"


def test_empty_input_yields_no_chunks():
    assert chunk_text("   \n  ", chunk_size=10, overlap=0) == []


def test_short_input_single_chunk():
    assert chunk_text("one two", chunk_size=10, overlap=2) == ["one two"]


def test_invalid_config_raises():
    with pytest.raises(ValueError):
        chunk_text("a b c", chunk_size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_text("a b c", chunk_size=3, overlap=3)


def test_chunk_id_stable_and_version_sensitive():
    a = chunk_id("d_1", 0, "v1")
    assert a == chunk_id("d_1", 0, "v1")
    assert a != chunk_id("d_1", 0, "v2")
    assert a != chunk_id("d_1", 1, "v1")


def test_content_hash_deterministic():
    assert content_hash("hello") == content_hash("hello")
    assert content_hash("hello") != content_hash("world")
