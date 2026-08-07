"""Regression tests for TG publish deduplication.

The picker walks teasers newest-first and takes the first one it has not already posted.
It used to build that "already posted" set from the current day's state file only, so each
morning it started at the top of the list again and re-sent the same articles. Combined
with a stalled image generator — which made every newer teaser unusable and pinned the walk
to one spot in the list — the channel published four articles, four times a day, for
seventeen days.
"""

from __future__ import annotations

import json

import pytest

from pipeline.stages import s10_pick_and_publish as pub


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Point the module at a throwaway STATE_DIR with a tg_published/ inside it."""
    (tmp_path / "tg_published").mkdir()
    monkeypatch.setattr(pub, "STATE_DIR", tmp_path)
    return tmp_path


def _write_day(state_dir, day: str, slugs_by_hour: dict[str, str]) -> None:
    payload = {h: {"slug": s, "msg_id": 1} for h, s in slugs_by_hour.items()}
    (state_dir / "tg_published" / f"{day}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_collects_slugs_across_every_day(state_dir):
    _write_day(state_dir, "2026-08-05", {"9": "alpha", "12": "beta"})
    _write_day(state_dir, "2026-08-06", {"9": "gamma"})
    _write_day(state_dir, "2026-08-07", {"9": "delta"})

    assert pub._all_posted_slugs() == {"alpha", "beta", "gamma", "delta"}


def test_yesterdays_article_is_not_a_candidate_today(state_dir):
    """The exact bug: a slug posted on an earlier day must stay excluded."""
    _write_day(state_dir, "2026-08-06", {"9": "alpha"})
    _write_day(state_dir, "2026-08-07", {"9": "beta"})

    assert "alpha" in pub._all_posted_slugs()


def test_missing_directory_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(pub, "STATE_DIR", tmp_path)
    assert pub._all_posted_slugs() == set()


def test_corrupt_day_is_skipped_not_fatal(state_dir):
    _write_day(state_dir, "2026-08-06", {"9": "alpha"})
    (state_dir / "tg_published" / "2026-08-07.json").write_text("{ truncated", encoding="utf-8")

    # One unreadable day costs at most a repeat; it must not take the publish run down.
    assert pub._all_posted_slugs() == {"alpha"}


def test_bare_string_entries_still_parse(state_dir):
    """Older state files stored the slug directly rather than a {slug, msg_id} dict."""
    (state_dir / "tg_published" / "2026-04-25.json").write_text(
        json.dumps({"9": "legacy-slug"}), encoding="utf-8"
    )
    assert pub._all_posted_slugs() == {"legacy-slug"}
