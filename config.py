import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_123')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hospital.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
