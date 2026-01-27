import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_ENGINE_OPTIONS = {
        # 'pool_pre_ping': True,
        # 'pool_recycle': 3600,
        # 'pool_size': 20,
        # 'max_overflow': 40
    }
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    ALPHA_VANTAGE_BASE_URL = 'https://www.alphavantage.co'


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite+pysqlite:///:memory:'
    SQLALCHEMY_ECHO = False
    COGNITO_REGION = ''
    COGNITO_USER_POOL_ID = ''
    COGNITO_APP_CLIENT_ID = ''
    ALPHA_VANTAGE_API_KEY = 'DUMMY_API_KEY'


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    COGNITO_REGION = os.environ.get('COGNITO_REGION')
    COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
    COGNITO_APP_CLIENT_ID = os.environ.get('COGNITO_APP_CLIENT_ID')
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or (
        f'mysql+pymysql://{os.environ.get("DB_USER", "")}:'
        f'{os.environ.get("DB_PASSWORD", "")}@'
        f'{os.environ.get("DB_HOST", "")}:'
        f'{os.environ.get("DB_PORT", "3306")}/'
        f'{os.environ.get("DB_NAME", "")}'
    )
    DEBUG = False
    SQLALCHEMY_ECHO = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'test': TestConfig,
}


def get_config(env: str):
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, DevelopmentConfig)
