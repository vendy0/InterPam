from flask import Blueprint, render_template, session, redirect, url_for, flash
from data import recuperer_utilisateur_par_username

# On crée le blueprint "admin"
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Un décorateur personnalisé pour vérifier si c'est un admin
def admin_required(f):
    def wrap(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        user = recuperer_utilisateur_par_username(session["username"])
        if user["role"] not in ["super_admin", "admin", "statisticien"]:
            flash("Accès interdit", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")
