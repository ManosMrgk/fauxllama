import os

class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.environ['PG_USER']}:{os.environ['PG_PASSWORD']}@"
        f"{os.environ['PG_HOST']}:{os.environ['PG_PORT']}/{os.environ['PG_DATABASE']}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False