from flask import request, Response
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from wtforms.fields import BooleanField
import os
from functools import wraps

from app.models import APIKey
from app.extensions import db

def check_auth(username, password):
    return username == 'admin' and password == os.environ.get('ADMIN_PASSWORD')

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


def setup_admin(app):
    admin = Admin(app, name='Admin Panel', template_mode='bootstrap4', index_view=MyAdminIndexView())
    admin.add_view(AuthModelView(APIKey, db.session, endpoint='apikey', name='API Keys', url='/apikeys'))
