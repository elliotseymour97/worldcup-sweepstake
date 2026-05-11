import json
import os
from flask import Flask
from models import db
from routes.main import main_bp
from routes.scores import scores_bp
from routes.admin import admin_bp
from routes.teams import teams_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object('config.Config')
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(scores_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teams_bp)

    with app.app_context():
        db.create_all()
        _migrate_db()
        _seed_countries()

    return app


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
