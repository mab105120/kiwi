from sqlalchemy.schema import CreateTable

from app import create_app
from app.config import get_config
from app.db import db

app = create_app(get_config('development'))

with app.app_context():
    for table in db.metadata.sorted_tables:
        print(CreateTable(table).compile(db.engine))
        print()
