import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
import os
import json
import uuid
from dotenv import load_dotenv
import requests
import atexit
from cachetools import TTLCache
from flask_limiter import Limiter
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from functools import wraps
from wtforms.fields import BooleanField
from flask_migrate import Migrate


load_dotenv()

def check_auth(username, password):
    return username == 'admin' and password == os.environ['ADMIN_PASSWORD']

def authenticate():
    return Response('Restricted Area', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

api_key_cache = TTLCache(maxsize=1000, ttl=60)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql://{os.environ['PG_USER']}:{os.environ['PG_PASSWORD']}@"
    f"{os.environ['PG_HOST']}:{os.environ['PG_PORT']}/{os.environ['PG_DATABASE']}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class APIKey(db.Model):
    __tablename__ = 'emeaik_pl_api_key'
    __table_args__ = {'schema': 'azure_ai'}

    eaik_id = db.Column(db.Integer, primary_key=True)
    eaik_username = db.Column(db.String)
    eaik_key = db.Column(db.String, server_default=text('gen_random_uuid()::text'))
    eaik_is_active = db.Column(db.Boolean, default=True, server_default=text('true'))
    # Add other fields as needed

    def __repr__(self):
        return f"<APIKey {self.eaik_username}>"

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

    def __repr__(self):
        return f"<Chat {self.eapc_conv_uuid} #{self.eapc_order}>"

class MyAdminIndexView(AdminIndexView):
    @requires_auth
    def _handle_view(self, name, **kwargs):
        return super()._handle_view(name, **kwargs)

    @expose('/')
    def index(self):
        return super().index()

def _is_active_formatter(view, context, model, name):
    return '✅' if model.eaik_is_active else '❌'

class AuthModelView(ModelView):
    column_formatters = {
        'eaik_is_active': _is_active_formatter
    }
    column_list = ('eaik_id', 'eaik_username', 'eaik_key', 'eaik_is_active')
    column_labels = {
        'eaik_id': 'ID',
        'eaik_username': 'Username',
        'eaik_key': 'API Key',
        'eaik_is_active': 'Active'
    }
    column_searchable_list = ('eaik_username',)
    column_filters = ('eaik_is_active',)
    form_overrides = {'eaik_is_active': BooleanField}
    form_widget_args = {
        'eaik_key': {'readonly': True, 'disabled': True},
    }
    form_args = {
        'eaik_is_active': {'default': True, 'description': 'Should this API key be enabled?'}
    }
    page_size = 25
    @requires_auth
    def _handle_view(self, name, **kwargs):
        return super()._handle_view(name, **kwargs)
        
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4', index_view=MyAdminIndexView())
admin.add_view(AuthModelView(APIKey, db.session, endpoint='apikey', name='API Keys', url='/apikeys'))

limiter = Limiter(app)

def get_curr_timestamp():
    return datetime.datetime.now()

# --- Database and AI Helpers (ALL SQLAlchemy) ---

def call_azure_openai(messages):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    key = os.environ["AZURE_OPENAI_KEY"]
    version = os.environ.get("AZURE_OPENAI_VERSION", "2024-12-01-preview")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}"
    headers = {"api-key": key, "Content-Type": "application/json"}
    data = {
        "messages": messages,
        "temperature": 0.1,
        "top_p": 1,
        "n": 1,
        "stream": True
    }
    with requests.post(url, headers=headers, json=data, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield line.decode("utf-8")

def authenticate_api_key(api_key):
    if api_key in api_key_cache:
        return api_key_cache[api_key]
    row = APIKey.query.filter_by(eaik_key=api_key).first()
    if not row:
        raise Exception("API key not found.")
    if not row.eaik_is_active:
        raise Exception("API key is inactive.")
    api_key_cache[api_key] = (row.eaik_id, row.eaik_username)
    return row.eaik_id, row.eaik_username

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
    if not messages:
        return
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
        )
        for i, m in enumerate(messages)
    ]
    db.session.bulk_save_objects(objs)
    db.session.commit()

def filter_user_model_messages(messages):
    return [m for m in messages if m['role'] in ('user', 'assistant', 'model')]

def log_conversation(messages, conv_id, username, model, apikey_id):
    log_chat_messages_batch(messages, conv_id, username, model, apikey_id)

# --- Utility for API Key in Path ---

def extract_api_key_and_path(path):
    segments = path.split('/')
    if len(segments) > 2 and segments[1]:
        api_key = segments[1]
        real_path = '/' + '/'.join(segments[2:])
    else:
        api_key = None
        real_path = path
    return api_key, real_path

# --- API Endpoints ---

@app.route('/<api_key>/api/models', methods=['GET'])
@app.route('/<api_key>/api/tags', methods=['GET'])
def api_models_tags(api_key):
    try:
        _, username = authenticate_api_key(api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    # Model info example
    model_info = {
        "models": [{
            "name": username,
            "model": username,
            "modified_at": "2025-07-18T15:51:16.1962348+03:00",
            "size": 3338801804,
            "digest": "a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a",
            "details": {
                "parent_model": "",
                "format": "gguf",
                "family": "gemma3",
                "families": ["gemma3"],
                "parameter_size": "4.3B",
                "quantization_level": "Q4_K_M"
            }
        }]
    }
    return jsonify(model_info)

@app.route('/<api_key>/api/show', methods=['POST'])
def api_show(api_key):
    try:
        _, username = authenticate_api_key(api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 401
    # Simulated show response
    show_info = {
        "modelfile": "# Modelfile for fake-gemma3\nFROM fake-gemma3\n",
        "parameters": "top_p 0.95\ntemperature 1\ntop_k 64",
        "template": "{{- range .Messages}}\n<|im_start|>{{ .Role }}\n{{ .Content }}<|im_end|>\n{{- end}}\n<|im_start|>assistant",
        "details": {
            "parent_model": "",
            "format": "gguf",
            "family": "gemma3",
            "families": ["gemma3"],
            "parameter_size": "4.3B",
            "quantization_level": "Q4_K_M"
        },
        "model_info": {
            "general.architecture": "gemma3",
            "general.parameter_count": 4300000000,
            "general.quantization_version": 2
        },
        "capabilities": ["completion", "vision"],
        "modified_at": "2025-07-18T15:51:16.1962348+03:00"
    }
    return jsonify(show_info)

@app.route('/<api_key>/v1/chat/completions', methods=['POST'])
@limiter.limit("10/minute")
def api_chat_completions(api_key):
    try:
        apikey_id, username = authenticate_api_key(api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    # Parse request
    request_json = request.get_json(force=True)
    messages = request_json['messages']
    chat_messages = filter_user_model_messages(messages)
    conv_id = str(uuid.uuid4())
    model = request_json.get('model', 'unknown')

    # Log user messages
    log_conversation([chat_messages[-1]], conv_id, username, model, apikey_id)
    # Call Azure OpenAI model
    def event_stream():
        assistant_reply = ""  # Collect full response
        for raw_line in call_azure_openai(chat_messages):
            # Azure streams as: data: {...}
            if raw_line.startswith("data: "):
                data_json = raw_line[len("data: "):].strip()
                if data_json == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break
                try:
                    data_obj = json.loads(data_json)
                    # Collect text for logging
                    delta = data_obj.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        assistant_reply += delta["content"]
                except Exception:
                    pass  # If the chunk isn't valid JSON, skip collecting
                yield raw_line + "\n\n"  # Forward as-is to client

        # After streaming, log the assistant reply
        log_chat_message(
            conv_id=conv_id,
            order=len(chat_messages),
            role='model',
            text=assistant_reply,
            username=username,
            model=model,
            apikey_id=apikey_id
        )

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    })

# --- Fallback for 404 ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

# --- Start Flask Server ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=11434, threaded=True)
