from .admin import setup_admin
from .routes import api_bp

def register_blueprints(app):
    # Register API blueprint
    app.register_blueprint(api_bp)
    
    # Setup Flask-Admin views
    setup_admin(app)