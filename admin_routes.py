from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from data import get_user_by_username, get_user_by_email, get_user_by_name, get_user_by_age, get_user_by_grade, ajouter_parieur

users_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Un décorateur personnalisé pour vérifier si c'est un admin
def admin_required(f):
    def wrap(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        user = get_user_by_username(session["username"])
        if user["role"] not in ["super_admin", "admin", "statisticien"]:
            flash("Accès interdit", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")


@users_bp.route("/")
@admin_required
def users():
	return render_template("admin/users.html")


@users_bp.route("/find-user", methods=['POST', 'GET'])
@admin_required
def find_user():
	if request.method == "GET":
		return render_template("admin/users/find_user.html")