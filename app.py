import os
from datetime import date
from flask import (Flask, render_template, redirect, url_for,
                   request, session, flash, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, close_db, init_db, seed_db
from auth import login_required, role_required

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

app.teardown_appcontext(close_db)

with app.app_context():
    init_db()
    seed_db()

CATEGORIES = ["Food", "Transport", "Utilities", "Entertainment",
              "Shopping", "Health", "Education", "Other"]


# ------------------------------------------------------------------ #
# Public routes                                                        #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")

        db = get_db()
        if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            return render_template("register.html", error="An account with this email already exists.")

        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'user')",
            (name, email, generate_password_hash(password))
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        flash("Welcome to Spendly!", "success")
        return redirect(url_for('dashboard'))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user or not check_password_hash(user['password_hash'], password):
            return render_template("login.html", error="Invalid email or password.")
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for('dashboard'))
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for('landing'))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Authenticated user routes                                            #
# ------------------------------------------------------------------ #

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    expenses = db.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC",
        (session['user_id'],)
    ).fetchall()
    total = sum(e['amount'] for e in expenses)
    month_prefix = date.today().strftime("%Y-%m")
    month_total = sum(e['amount'] for e in expenses if e['date'].startswith(month_prefix))
    month_name = date.today().strftime("%B %Y")
    return render_template("dashboard.html", expenses=expenses, total=total,
                           month_total=month_total, month_name=month_name)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")

        if not name:
            return render_template("profile.html", user=user, error="Name cannot be empty.")
        if new_pw:
            if len(new_pw) < 8:
                return render_template("profile.html", user=user,
                                       error="New password must be at least 8 characters.")
            if not check_password_hash(user['password_hash'], current_pw):
                return render_template("profile.html", user=user,
                                       error="Current password is incorrect.")
            db.execute("UPDATE users SET name = ?, password_hash = ? WHERE id = ?",
                       (name, generate_password_hash(new_pw), session['user_id']))
        else:
            db.execute("UPDATE users SET name = ? WHERE id = ?", (name, session['user_id']))
        db.commit()
        session['user_name'] = name
        flash("Profile updated.", "success")
        return redirect(url_for('profile'))
    return render_template("profile.html", user=user)


@app.route("/expenses/add", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_raw = request.form.get("amount", "")
        category = request.form.get("category", "")
        exp_date = request.form.get("date", "")
        note = request.form.get("note", "").strip()

        if not title or not amount_raw or not category or not exp_date:
            return render_template("expenses/add.html", categories=CATEGORIES,
                                   form=request.form, error="Title, amount, category, and date are required.")
        if category not in CATEGORIES:
            return render_template("expenses/add.html", categories=CATEGORIES,
                                   form=request.form, error="Invalid category.")
        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render_template("expenses/add.html", categories=CATEGORIES,
                                   form=request.form, error="Amount must be a positive number.")

        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, title, amount, category, date, note) VALUES (?, ?, ?, ?, ?, ?)",
            (session['user_id'], title, amount, category, exp_date, note)
        )
        db.commit()
        flash("Expense added.", "success")
        return redirect(url_for('dashboard'))
    return render_template("expenses/add.html", categories=CATEGORIES, form={})


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    db = get_db()
    expense = db.execute("SELECT * FROM expenses WHERE id = ?", (id,)).fetchone()
    if not expense:
        abort(404)
    if session['user_role'] != 'admin' and expense['user_id'] != session['user_id']:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_raw = request.form.get("amount", "")
        category = request.form.get("category", "")
        exp_date = request.form.get("date", "")
        note = request.form.get("note", "").strip()
        form_data = dict(title=title, amount=amount_raw, category=category,
                         date=exp_date, note=note)

        if not title or not amount_raw or not category or not exp_date:
            return render_template("expenses/edit.html", categories=CATEGORIES,
                                   form=form_data, expense_id=id,
                                   error="Title, amount, category, and date are required.")
        if category not in CATEGORIES:
            return render_template("expenses/edit.html", categories=CATEGORIES,
                                   form=form_data, expense_id=id, error="Invalid category.")
        try:
            amount = float(amount_raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            return render_template("expenses/edit.html", categories=CATEGORIES,
                                   form=form_data, expense_id=id,
                                   error="Amount must be a positive number.")

        db.execute(
            "UPDATE expenses SET title=?, amount=?, category=?, date=?, note=? WHERE id=?",
            (title, amount, category, exp_date, note, id)
        )
        db.commit()
        flash("Expense updated.", "success")
        return redirect(url_for('dashboard'))

    form_data = dict(title=expense['title'], amount=expense['amount'],
                     category=expense['category'], date=expense['date'],
                     note=expense['note'] or '')
    return render_template("expenses/edit.html", categories=CATEGORIES,
                           form=form_data, expense_id=id)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
@login_required
def delete_expense(id):
    db = get_db()
    expense = db.execute("SELECT * FROM expenses WHERE id = ?", (id,)).fetchone()
    if not expense:
        abort(404)
    if session['user_role'] != 'admin' and expense['user_id'] != session['user_id']:
        abort(403)
    db.execute("DELETE FROM expenses WHERE id = ?", (id,))
    db.commit()
    flash("Expense deleted.", "success")
    return redirect(url_for('dashboard'))


# ------------------------------------------------------------------ #
# Admin routes                                                         #
# ------------------------------------------------------------------ #

@app.route("/admin")
@role_required('admin')
def admin_dashboard():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    total_users = len(users)
    total_expenses = db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    total_amount = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses"
    ).fetchone()[0]
    recent_expenses = db.execute(
        """SELECT e.*, u.name AS user_name
           FROM expenses e
           JOIN users u ON e.user_id = u.id
           ORDER BY e.created_at DESC LIMIT 10"""
    ).fetchall()
    return render_template("admin.html", users=users, total_users=total_users,
                           total_expenses=total_expenses, total_amount=total_amount,
                           recent_expenses=recent_expenses)


@app.route("/admin/users/<int:id>/role", methods=["POST"])
@role_required('admin')
def admin_change_role(id):
    new_role = request.form.get("role")
    if new_role not in ('user', 'admin'):
        abort(400)
    if id == session['user_id']:
        flash("You cannot change your own role.", "error")
        return redirect(url_for('admin_dashboard'))
    db = get_db()
    if not db.execute("SELECT id FROM users WHERE id = ?", (id,)).fetchone():
        abort(404)
    db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, id))
    db.commit()
    flash("User role updated.", "success")
    return redirect(url_for('admin_dashboard'))


# ------------------------------------------------------------------ #
# Error handlers                                                       #
# ------------------------------------------------------------------ #

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5001)
