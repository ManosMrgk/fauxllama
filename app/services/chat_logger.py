from ..models import Chat
from ..extensions import db
import datetime

def get_curr_timestamp():
    return datetime.datetime.now()

def log_chat_message(conv_id, order, role, text, username, model, apikey_id):
    chat = Chat(
        eapc_conv_uuid=conv_id,
        eapc_order=order,
        eapc_role=role,
        eapc_text=text,
        eapc_username=username,
        eapc_model=model,
        eaik_id=apikey_id,
        usrinsert=username,
        dteinsert=get_curr_timestamp(),
        row_version=0
    )
    db.session.add(chat)
    db.session.commit()
    return chat.eapc_id

def log_chat_messages_batch(messages, conv_id, username, model, apikey_id):
    objs = [
        Chat(
            eapc_conv_uuid=conv_id,
            eapc_order=i,
            eapc_role=m['role'],
            eapc_text=m['content'],
            eapc_username=username,
            eapc_model=model,
            eaik_id=apikey_id,
            usrinsert=username,
            dteinsert=get_curr_timestamp(),
            row_version=0
        ) for i, m in enumerate(messages)
    ]
    db.session.bulk_save_objects(objs)
    db.session.commit()

def log_conversation(messages, conv_id, username, model, apikey_id):
    log_chat_messages_batch(messages, conv_id, username, model, apikey_id)