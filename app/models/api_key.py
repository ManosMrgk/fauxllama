from app.extensions import db
from sqlalchemy import text

class APIKey(db.Model):
    __tablename__ = 'emeaik_pl_api_key'
    __table_args__ = {'schema': 'azure_ai'}

    eaik_id = db.Column(db.Integer, primary_key=True)
    eaik_username = db.Column(db.String)
    eaik_key = db.Column(db.String, server_default=text('gen_random_uuid()::text'))
    eaik_is_active = db.Column(db.Boolean, default=True, server_default=text('true'))