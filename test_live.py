"""
Live match simulator for UI testing before the real thing.

Usage:
  python test_live.py          — create a fake IN_PLAY match between two assigned countries
  python test_live.py goal     — score a goal (triggers toast on next poll)
  python test_live.py ht       — set half time (PAUSED)
  python test_live.py finish   — end the match
  python test_live.py reset    — delete the test match and clean up
"""
import sys
import json
from app import create_app

FAKE_API_ID = 99999


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'live'
    app = create_app()

    with app.app_context():
        from models import db, Country, Match

        # Prefer countries with players assigned; fall back to any two countries
        assigned = Country.query.filter(Country.player_id.isnot(None)).all()
        all_countries = Country.query.all()
        pool = assigned if len(assigned) >= 2 else all_countries
        if len(pool) < 2:
            print("ERROR: No countries seeded yet. Start the app first to seed the DB.")
            return

        home, away = pool[0], pool[1]
        match = Match.query.filter_by(api_id=FAKE_API_ID).first()

        if cmd == 'reset':
            if match:
                db.session.delete(match)
                db.session.commit()
                print("OK Test match deleted.")
            else:
                print("No test match to delete.")
            return

        if not match:
            from datetime import datetime
            match = Match(
                api_id=FAKE_API_ID,
                home_team_name=home.name,
                away_team_name=away.name,
                home_team_id=home.id,
                away_team_id=away.id,
                home_score=0,
                away_score=0,
                stage='GROUP_STAGE',
                group_name=home.group_name,
                status='IN_PLAY',
                minute=1,
                kickoff=datetime.utcnow(),
                last_updated=datetime.utcnow(),
            )
            db.session.add(match)

        if cmd in ('live', 'start'):
            match.status = 'IN_PLAY'
            match.home_score = match.home_score if match.home_score is not None else 0
            match.away_score = match.away_score if match.away_score is not None else 0
            match.minute = match.minute or 1
            print(f"OK LIVE: {home.name} {match.home_score}–{match.away_score} {away.name} ({match.minute}')")

        elif cmd == 'goal':
            match.home_score = (match.home_score or 0) + 1
            match.minute = min((match.minute or 1) + 12, 45)
            goals = json.loads(match.goals_json or '[]')
            goals.append({
                'minute': str(match.minute),
                'scorer': 'Test Scorer',
                'is_home': True,
                'type': 'REGULAR',
            })
            match.goals_json = json.dumps(goals)
            print(f"OK GOAL: {home.name} {match.home_score}–{match.away_score} {away.name} ({match.minute}')")
            print("  Reload the scores page — the next HTMX poll will trigger a goal toast.")

        elif cmd == 'ht':
            match.status = 'PAUSED'
            match.minute = 45
            print(f"OK HALF TIME: {home.name} {match.home_score}–{match.away_score} {away.name}")

        elif cmd == 'finish':
            match.status = 'FINISHED'
            print(f"OK FINISHED: {home.name} {match.home_score}–{match.away_score} {away.name}")

        else:
            print(f"Unknown command: {cmd!r}. Use: live, goal, ht, finish, reset")
            return

        db.session.commit()
        print(f"  home_id={match.home_team_id}  away_id={match.away_team_id}")


if __name__ == '__main__':
    main()
