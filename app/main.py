from app import create_app
from app.config import get_config

app_config = get_config("development")
app = create_app(app_config)

if __name__ == "__main__":
    app.run()
