from flask import Flask
from .extensions import db, migrate, limiter
from .models import *  # Import models so Alembic sees them
from .views import register_blueprints
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY")
    app.config.from_object('app.config.Config')
    app.config.from_prefixed_env()
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    register_blueprints(app)

    return app