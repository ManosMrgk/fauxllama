import datetime
from app.extensions import db

class Chat(db.Model):
    __tablename__ = 'emeaik_pl_chat'
    __table_args__ = {'schema': 'azure_ai'}

    eapc_id = db.Column(db.Integer, primary_key=True)
    eapc_conv_uuid = db.Column(db.String)
    eapc_order = db.Column(db.Integer)
    eapc_role = db.Column(db.String)
    eapc_text = db.Column(db.Text)
    eapc_username = db.Column(db.String)
    eapc_model = db.Column(db.String)
    eaik_id = db.Column(db.Integer)
    usrinsert = db.Column(db.String)
    dteinsert = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    row_version = db.Column(db.Integer, default=0)