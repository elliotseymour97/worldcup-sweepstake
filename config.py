import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///sweepstake.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY', '')
    COMPETITION_CODE = os.environ.get('COMPETITION_CODE', 'WC')
