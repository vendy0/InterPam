from functools import wraps
from flask import session, request


def active_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" in session:
            user = get_user_by_username(session["username"])
            if not user or not bool(user["actif"]):
                session.clear()
                flash("Votre compte a été suspendu.", "error")
                return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def bloquer_doublons(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # On ne bloque QUE les envois de données
        if request.method == "POST":
            if session.get("is_processing"):
                flash("Traitement en cours, patientez...", "warning")
                return redirect(request.referrer or url_for("users.manage_users"))

            session["is_processing"] = True
            try:
                return f(*args, **kwargs)
            finally:
                session.pop("is_processing", None)

        # Pour le GET, on laisse passer normalement
        return f(*args, **kwargs)

    return decorated_function
