import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///app.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PROVIDER_TYPE = os.environ.get('PROVIDER_TYPE', 'static')
    BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY', '')
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
