import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, storage_uri=os.environ.get("RATELIMIT_STORAGE_URL"))