import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith(('postgres://', 'postgresql://')):
        SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///sweepstake.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY', '')
    COMPETITION_CODE = os.environ.get('COMPETITION_CODE', 'WC')
    ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'GoodisonPark97!')
