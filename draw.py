import random
from models import db, Player, Country


def run_draw(player_names):
    names = [n.strip() for n in player_names if n.strip()]
    if len(names) != 6:
        raise ValueError('Exactly 6 player names are required.')

    Country.query.update({'player_id': None})
    Player.query.delete()
    db.session.flush()

    players = [Player(name=name) for name in names]
    db.session.add_all(players)
    db.session.flush()

    for tier in range(1, 5):
        tier_countries = Country.query.filter_by(tier=tier).all()
        if len(tier_countries) != 12:
            raise ValueError(f'Expected 12 tier-{tier} countries, found {len(tier_countries)}.')
        random.shuffle(tier_countries)
        for i, country in enumerate(tier_countries):
            country.player_id = players[i % len(players)].id

    db.session.commit()
    return players
