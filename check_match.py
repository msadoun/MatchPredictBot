from datetime import datetime

from database import get_db, init_db, match_accepts_predictions, _row_to_match
from worldcup2026 import kickoff_datetime, WORLD_CUP_2026_FIXTURES, kickoff_label

init_db()
fixture = next(
    f for f in WORLD_CUP_2026_FIXTURES if f.home == "هولندا" and f.away == "السويد"
)
print("fixture label:", kickoff_label(fixture))
print("fixture kickoff utc:", kickoff_datetime(kickoff_label(fixture)))
print("now utc:", datetime.utcnow())

with get_db() as conn:
    row = conn.execute(
        "SELECT * FROM matches WHERE home_team = ? AND away_team = ?",
        ("هولندا", "السويد"),
    ).fetchone()
if row:
    m = _row_to_match(row)
    print("db kickoff_at:", m.kickoff_at)
    print("db kickoff utc:", kickoff_datetime(m.kickoff_at or ""))
    print("accepts predictions:", match_accepts_predictions(m))
