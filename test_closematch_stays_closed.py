""" /closematch must stay closed even when kickoff is still in the future."""

import importlib
import os
import tempfile
from datetime import datetime, timedelta


def _fresh():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    return db


def test_closematch_locks_against_sync_reopen():
    db = _fresh()
    kickoff = (datetime.utcnow() + timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%S · الجولة 5 · الدوري الإنجليزي"
    )
    match = db.add_match("برايتون", "أرسنال", kickoff)
    assert db.match_accepts_predictions(match)

    db.close_match(match.id)
    closed = db.get_match(match.id)
    assert closed is not None
    assert not closed.is_open
    assert closed.predictions_override
    assert not db.match_accepts_predictions(closed)

    # Periodic sync used to reopen future matches after /closematch.
    updated = db.sync_match_open_flags()
    after_sync = db.get_match(match.id)
    assert after_sync is not None
    assert not after_sync.is_open
    assert after_sync.predictions_override
    assert not db.match_accepts_predictions(after_sync)
    assert updated == 0 or not after_sync.is_open


def test_openmatch_still_force_opens_after_close():
    db = _fresh()
    kickoff = (datetime.utcnow() + timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%S · الجولة 5 · الدوري الإنجليزي"
    )
    match = db.add_match("برايتون", "أرسنال", kickoff)
    db.close_match(match.id)
    assert not db.match_accepts_predictions(db.get_match(match.id))

    reopened = db.open_match(match.id)
    assert reopened is not None
    assert reopened.is_open
    assert reopened.predictions_override
    assert db.match_accepts_predictions(reopened)


def test_set_result_does_not_reopen_closed_override():
    db = _fresh()
    kickoff = (datetime.utcnow() + timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%S · الجولة 5 · الدوري الإنجليزي"
    )
    match = db.add_match("برايتون", "أرسنال", kickoff)
    db.close_match(match.id)

    scored = db.set_match_result(match.id, 1, 0)
    assert scored is not None
    assert not scored.is_open
    assert scored.predictions_override
    assert not db.match_accepts_predictions(scored)
