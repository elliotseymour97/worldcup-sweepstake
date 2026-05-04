from __future__ import annotations

import requests
from datetime import datetime, timedelta
from typing import Optional
from flask import current_app
from models import db, Country, Match

_last_fetch: Optional[datetime] = None

STAGE_MAP = {
    'GROUP_STAGE':    'GROUP_STAGE',
    'LAST_32':        'LAST_32',
    'LAST_16':        'LAST_16',
    'QUARTER_FINALS': 'QUARTER_FINALS',
    'SEMI_FINALS':    'SEMI_FINALS',
    'THIRD_PLACE':    'THIRD_PLACE',
    'FINAL':          'FINAL',
}


def _find_country(api_name: str) -> Optional[Country]:
    c = Country.query.filter(
        db.func.lower(Country.api_name) == api_name.lower()
    ).first()
    if not c:
        c = Country.query.filter(
            db.func.lower(Country.name) == api_name.lower()
        ).first()
    return c


def fetch_and_sync() -> tuple[bool, str]:
    global _last_fetch

    api_key = current_app.config.get('FOOTBALL_DATA_API_KEY', '')
    if not api_key:
        return False, 'No API key configured — add FOOTBALL_DATA_API_KEY to your .env file.'

    now = datetime.utcnow()
    if _last_fetch and (now - _last_fetch) < timedelta(seconds=60):
        return True, 'Data is fresh (last synced < 60 s ago).'

    competition = current_app.config.get('COMPETITION_CODE', 'WC')
    url = f'https://api.football-data.org/v4/competitions/{competition}/matches'

    try:
        resp = requests.get(url, headers={'X-Auth-Token': api_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return False, f'API request failed: {e}'

    matches = data.get('matches', [])
    _sync_matches(matches)
    _last_fetch = now
    return True, f'Synced {len(matches)} matches.'


def _sync_matches(api_matches: list) -> None:
    for m in api_matches:
        api_id    = m.get('id')
        home_name = m.get('homeTeam', {}).get('name', '')
        away_name = m.get('awayTeam', {}).get('name', '')
        stage     = STAGE_MAP.get(m.get('stage', ''), m.get('stage', ''))
        status    = m.get('status', 'SCHEDULED')

        ft         = m.get('score', {}).get('fullTime', {})
        home_score = ft.get('home')
        away_score = ft.get('away')

        kickoff_str = m.get('utcDate')
        kickoff = None
        if kickoff_str:
            try:
                kickoff = datetime.fromisoformat(kickoff_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        group_raw  = m.get('group') or ''
        group_letter = group_raw.replace('GROUP_', '') if group_raw.startswith('GROUP_') else None

        home_country = _find_country(home_name)
        away_country = _find_country(away_name)

        match = Match.query.filter_by(api_id=api_id).first()
        if not match:
            match = Match(api_id=api_id)
            db.session.add(match)

        match.home_team_name = home_name
        match.away_team_name = away_name
        match.home_team_id   = home_country.id if home_country else None
        match.away_team_id   = away_country.id if away_country else None
        match.home_score     = home_score
        match.away_score     = away_score
        match.stage          = stage
        match.group_name     = group_letter
        match.status         = status
        match.kickoff        = kickoff
        match.last_updated   = datetime.utcnow()

    db.session.commit()
