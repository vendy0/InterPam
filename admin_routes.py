from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from data import get_user_by_username, get_user_by_email, get_user_by_name, get_user_by_age, get_user_by_grade, ajouter_parieur, filtrer_users_admin, credit

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



"""
---------------------------------------
ROUTES DES USERS
---------------------------------------
"""
@users_bp.route("/")
@admin_required
def users():
	return render_template("admin/users.html")


@users_bp.route("/find-user", methods=['POST', 'GET'])
@admin_required
def find_user():
    if request.method == "GET":
        return render_template("admin/users.html")
    
    criteres = {
        "nom": request.form.get("nom"),
        "username": request.form.get("username_finding"),
        "email": request.form.get("email"),
        "age": request.form.get("age"),
        "classe": request.form.get("classe")
    }
    
    # On appelle la fonction de filtrage strict (AND)
    resultats = filtrer_users_admin(criteres)
    if len(resultats) > 0:
    	return render_template("admin/users.html", users=resultats)
    else:
    	return render_template("admin/users.html", no_users="no users")

@users_bp.route("/credit", methods=["GET", "POST"])
@admin_required
def credit_user():
	if request.method == "GET":
		return render_template("admin/users.html")
	donnees = request.form
	username = donnees.get("username_credit")
	try:
		solde = float(donnees.get("solde"))
		solde_centime = int(round(solde * 100))
	except:
		flash("Vous devez entrer un nombre !")
		return render_template("admin/users.html")
		
	succes, message = credit(username, solde_centime)
	if succes:
		flash(message)
		return render_template('admin/users.html')
	else:
		flash(message)
		return render_template('admin/users.html')
	
