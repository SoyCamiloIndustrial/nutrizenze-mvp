# app/__init__.py
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configuración
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
    
    return app
