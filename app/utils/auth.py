import os
from functools import wraps
from flask import request, Response
from cachetools import TTLCache
from ..models import APIKey
from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, expose
from wtforms.fields import BooleanField

api_key_cache = TTLCache(maxsize=1000, ttl=60)

def authenticate_api_key(api_key):
    if api_key in api_key_cache:
        return api_key_cache[api_key]
    row = APIKey.query.filter_by(eaik_key=api_key).first()
    if not row or not row.eaik_is_active:
        raise Exception("Invalid or inactive API key")
    api_key_cache[api_key] = (row.eaik_id, row.eaik_username)
    return row.eaik_id, row.eaik_username

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

class MyAdminIndexView(AdminIndexView):
    @requires_auth
    def _handle_view(self, name, **kwargs):
        return super()._handle_view(name, **kwargs)

    @expose('/')
    def index(self):
        return super().index()

class AuthModelView(ModelView):
    column_formatters = {
        'eaik_is_active': lambda v, c, m, p: '✅' if m.eaik_is_active else '❌'
    }
    column_list = ('eaik_id', 'eaik_username', 'eaik_key', 'eaik_is_active')
    form_overrides = {'eaik_is_active': BooleanField}
    form_widget_args = {'eaik_key': {'readonly': True, 'disabled': True}}
    form_args = {'eaik_is_active': {'default': True}}

    @requires_auth
    def _handle_view(self, name, **kwargs):
        return super()._handle_view(name, **kwargs)