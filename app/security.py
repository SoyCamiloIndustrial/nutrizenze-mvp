# app/security.py
"""Seguridad: configuración, inicio de sesión por roles, CSRF y cabeceras.

Roles:
- medico: ve todos los pacientes, su historial y alertas; usa la API.
- paciente: ve solo su propio resumen y sus recomendaciones aprobadas.

Variables de entorno (ver .env.example):
- APP_ENV=production   activa cookies Secure, HSTS y exige SECRET_KEY.
- SECRET_KEY           firma la cookie de sesión. Obligatoria en producción.
- DEMO_MODE=1          crea usuarios de demostración (datos ficticios).
- DEMO_PASSWORD        contraseña de los usuarios demo. Obligatoria en
                       producción si DEMO_MODE=1; en desarrollo se genera una.
"""
import hmac
import logging
import os
import secrets
import time
from datetime import timedelta
from functools import wraps
from urllib.parse import urlparse

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

log = logging.getLogger("vitaltrace")
audit_log = logging.getLogger("vitaltrace.audit")

auth = Blueprint("auth", __name__)

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
SESSION_MINUTES = 30

# Usuarios de demostración: enlazados a los pacientes ficticios de demo_patients.json.
DEMO_USERS = [
    {"username": "medico.demo", "name": "Médico Demo", "role": "medico", "patient_id": None},
    {"username": "paciente.uno", "name": "Paciente Demo Uno", "role": "paciente", "patient_id": "demo-001"},
    {"username": "paciente.dos", "name": "Paciente Demo Dos", "role": "paciente", "patient_id": "demo-002"},
]


class UserStore:
    """Usuarios en memoria con contraseñas cifradas (hash). Reemplazar por BD."""

    def __init__(self):
        self._users = {}

    def add(self, username, password, role, name, patient_id=None):
        self._users[username] = {
            "username": username, "name": name, "role": role, "patient_id": patient_id,
            "password_hash": generate_password_hash(password),
        }

    def authenticate(self, username, password):
        user = self._users.get(username)
        if user is None:
            # Comparar contra un hash falso para no revelar si el usuario existe por el tiempo de respuesta.
            check_password_hash(_DUMMY_HASH, password)
            return None
        return user if check_password_hash(user["password_hash"], password) else None

    def get(self, username):
        return self._users.get(username)

    def __len__(self):
        return len(self._users)


_DUMMY_HASH = generate_password_hash(secrets.token_hex(16))
users = UserStore()
_failed_logins = {}


def is_production():
    return os.environ.get("APP_ENV", "development").lower() == "production"


def init_security(app):
    production = is_production()
    secret = os.environ.get("SECRET_KEY")
    if production and (not secret or len(secret) < 32):
        raise RuntimeError("SECRET_KEY es obligatoria en producción (mínimo 32 caracteres).")

    app.config.update(
        SECRET_KEY=secret or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=SESSION_MINUTES),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if production:
        # Railway termina TLS en su proxy; confiar en X-Forwarded-* de un salto.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _load_demo_users(production)

    app.register_blueprint(auth)
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.before_request(_load_user)
    app.before_request(_protect_api)
    app.before_request(_check_csrf)
    app.after_request(_security_headers)


def _load_demo_users(production):
    if os.environ.get("DEMO_MODE", "0" if production else "1") != "1":
        return
    password = os.environ.get("DEMO_PASSWORD")
    if not password:
        if production:
            raise RuntimeError("DEMO_PASSWORD es obligatoria cuando DEMO_MODE=1 en producción.")
        password = secrets.token_urlsafe(9)
        log.warning("Usuarios demo creados con contraseña temporal: %s", password)
    if production and len(password) < 12:
        raise RuntimeError("DEMO_PASSWORD debe tener al menos 12 caracteres en producción.")
    for u in DEMO_USERS:
        users.add(u["username"], password, u["role"], u["name"], u["patient_id"])


# ===== Sesión y roles =====
def _load_user():
    username = session.get("user")
    g.user = users.get(username) if username else None


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def _protect_api():
    """La API (salvo /api/health) solo responde a médicos con sesión."""
    if not request.path.startswith("/api") or request.path == "/api/health":
        return None
    if g.user is None:
        return jsonify({"status": "error", "message": "Autenticación requerida"}), 401
    if g.user["role"] != "medico":
        return jsonify({"status": "error", "message": "Acceso no permitido"}), 403
    return None


def audit(action, **detail):
    who = g.user["username"] if getattr(g, "user", None) else "anonimo"
    audit_log.info("%s usuario=%s ip=%s %s", action, who, request.remote_addr,
                   " ".join(f"{k}={v}" for k, v in detail.items()))


# ===== CSRF =====
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _check_csrf():
    if request.method != "POST" or request.path.startswith("/api"):
        return None
    sent = request.form.get("csrf_token", "")
    expected = session.get("csrf", "")
    if not expected or not hmac.compare_digest(sent, expected):
        abort(400, "Token CSRF inválido")
    return None


# ===== Cabeceras =====
def _security_headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if g.get("user"):
        resp.headers["Cache-Control"] = "no-store"
    if is_production():
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


# ===== Login =====
def _safe_next(target):
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


def _home_for(user):
    return url_for("views.doctor_home") if user["role"] == "medico" else url_for("views.patient_home")


def _locked(key):
    attempts = [t for t in _failed_logins.get(key, []) if time.time() - t < LOCKOUT_SECONDS]
    _failed_logins[key] = attempts
    return len(attempts) >= MAX_FAILED_LOGINS


@auth.route("/login", methods=["GET", "POST"])
def login():
    next_url = _safe_next(request.values.get("next"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        key = (request.remote_addr, username)
        if _locked(key):
            audit("login_bloqueado", cuenta=username)
            flash("Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo.")
            return render_template("login.html", next=next_url), 429
        user = users.authenticate(username, request.form.get("password", ""))
        if user is None:
            _failed_logins.setdefault(key, []).append(time.time())
            audit("login_fallido", cuenta=username)
            flash("Usuario o contraseña incorrectos.")
            return render_template("login.html", next=next_url), 401
        _failed_logins.pop(key, None)
        session.clear()
        session.permanent = True
        session["user"] = user["username"]
        g.user = user
        audit("login_ok")
        return redirect(next_url or _home_for(user))
    return render_template("login.html", next=next_url)


@auth.route("/logout", methods=["POST"])
def logout():
    audit("logout")
    session.clear()
    return redirect(url_for("views.portal"))
