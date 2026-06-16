import json
import os
import threading
import time
from flask import Flask
from models import db
from routes.main import main_bp
from routes.scores import scores_bp
from routes.admin import admin_bp
from routes.teams import teams_bp

try:
    from flask_compress import Compress
    _compress = Compress()
except ImportError:
    _compress = None


PLAYER_COLORS = ['emerald', 'blue', 'violet', 'amber', 'rose', 'cyan']

# FIFA 3-letter code → ISO 3166-1 alpha-2 (for flagcdn.com)
_FIFA_TO_ISO2 = {
    'MEX': 'mx', 'KOR': 'kr', 'CZE': 'cz', 'RSA': 'za', 'SUI': 'ch',
    'CAN': 'ca', 'QAT': 'qa', 'BIH': 'ba', 'BRA': 'br', 'MAR': 'ma',
    'SCO': 'gb-sct', 'HAI': 'ht', 'USA': 'us', 'AUS': 'au', 'TUR': 'tr',
    'PAR': 'py', 'GER': 'de', 'ECU': 'ec', 'CIV': 'ci', 'CUW': 'cw',
    'NED': 'nl', 'JPN': 'jp', 'SWE': 'se', 'TUN': 'tn', 'BEL': 'be',
    'IRN': 'ir', 'EGY': 'eg', 'NZL': 'nz', 'ESP': 'es', 'URU': 'uy',
    'KSA': 'sa', 'CPV': 'cv', 'FRA': 'fr', 'SEN': 'sn', 'NOR': 'no',
    'IRQ': 'iq', 'ARG': 'ar', 'AUT': 'at', 'ALG': 'dz', 'JOR': 'jo',
    'POR': 'pt', 'COL': 'co', 'COD': 'cd', 'UZB': 'uz', 'ENG': 'gb-eng',
    'CRO': 'hr', 'GHA': 'gh', 'PAN': 'pa',
}


def _flag_url(code: str) -> str:
    iso = _FIFA_TO_ISO2.get(code, code.lower())
    return f'https://flagcdn.com/20x15/{iso}.png'


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object('config.Config')
    if test_config:
        app.config.update(test_config)

    if _compress:
        _compress.init_app(app)
    db.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(scores_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teams_bp)

    app.jinja_env.globals['player_color'] = lambda pid: PLAYER_COLORS[int(pid) % len(PLAYER_COLORS)]
    app.jinja_env.globals['flag_url'] = _flag_url

    with app.app_context():
        db.create_all()
        _migrate_db()
        _seed_countries()

    _start_sync_worker(app)
    return app


def _start_sync_worker(app):
    """Start a single background thread that syncs from the API every 30 seconds.
    This replaces per-request background threads, which had race conditions and
    silent failures with no visibility into errors."""
    def _worker():
        time.sleep(5)  # let the app finish starting up
        while True:
            try:
                with app.app_context():
                    from api_client import _do_sync
                    _do_sync()
            except Exception:
                pass
            time.sleep(30)
    t = threading.Thread(target=_worker, daemon=True, name='api-sync')
    t.start()


def _migrate_db():
    from sqlalchemy import text
    new_cols = [
        ('minute',        'INTEGER'),
        ('goals_json',    'TEXT'),
        ('bookings_json', 'TEXT'),
    ]
    for col, typ in new_cols:
        with db.engine.connect() as conn:
            try:
                conn.execute(text(f'ALTER TABLE matches ADD COLUMN IF NOT EXISTS {col} {typ}'))
                conn.commit()
            except Exception:
                conn.rollback()


def _seed_countries():
    from models import Country
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'countries.json')
    with open(data_path, encoding='utf-8') as f:
        countries = json.load(f)

    if Country.query.count() == 0:
        for c in countries:
            db.session.add(Country(
                name=c['name'],
                code=c['code'],
                api_name=c['api_name'],
                group_name=c['group'],
                tier=c['tier'],
                fifa_ranking=c['fifa_ranking'],
            ))
    else:
        # Update metadata for existing countries by code so deployments fix stale data.
        # player_id is intentionally not touched — draw assignments are preserved.
        for c in countries:
            existing = Country.query.filter_by(code=c['code']).first()
            if existing:
                existing.name = c['name']
                existing.api_name = c['api_name']
                existing.tier = c['tier']
                existing.group_name = c['group']
                existing.fifa_ranking = c['fifa_ranking']
    db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
