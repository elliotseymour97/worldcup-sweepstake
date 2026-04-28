from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    countries = db.relationship('Country', back_populates='player', lazy='select')

    def __repr__(self):
        return f'<Player {self.name}>'


class Country(db.Model):
    __tablename__ = 'countries'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(3))
    api_name = db.Column(db.String(100))
    group_name = db.Column(db.String(1))
    tier = db.Column(db.Integer)
    fifa_ranking = db.Column(db.Integer)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    player = db.relationship('Player', back_populates='countries')

    home_matches = db.relationship(
        'Match', foreign_keys='Match.home_team_id',
        back_populates='home_country', lazy='select'
    )
    away_matches = db.relationship(
        'Match', foreign_keys='Match.away_team_id',
        back_populates='away_country', lazy='select'
    )

    @property
    def multiplier(self):
        return {1: 1.0, 2: 1.25, 3: 1.5, 4: 1.75}[self.tier]

    @property
    def tier_label(self):
        return {1: 'Favourite', 2: '2nd Seed', 3: '3rd Seed', 4: 'Underdog'}[self.tier]

    def __repr__(self):
        return f'<Country {self.name}>'


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    api_id = db.Column(db.Integer, unique=True, nullable=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('countries.id'), nullable=True)
    away_team_id = db.Column(db.Integer, db.ForeignKey('countries.id'), nullable=True)
    home_country = db.relationship('Country', foreign_keys=[home_team_id], back_populates='home_matches')
    away_country = db.relationship('Country', foreign_keys=[away_team_id], back_populates='away_matches')
    home_team_name = db.Column(db.String(100))
    away_team_name = db.Column(db.String(100))
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    stage = db.Column(db.String(50))
    group_name = db.Column(db.String(2), nullable=True)
    status = db.Column(db.String(20), default='SCHEDULED')
    kickoff = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Match {self.home_team_name} vs {self.away_team_name}>'
