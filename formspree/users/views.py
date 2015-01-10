from flask import request, flash, url_for, render_template, redirect, jsonify
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from helpers import check_password
from formspree.app import DB
from models import User

def register():
    if request.method == 'GET':
        return render_template('register.html')
    try:
        user = User(request.form['email'], request.form['password'])
        DB.session.add(user)
        DB.session.commit()

    except IntegrityError:
        DB.session.rollback()
        flash("An account with this email already exists.", "error")
        return render_template('register.html')

    login_user(user)
    flash('Your account is successfully registered.')

    print "Dashboard:"

    return redirect(url_for('dashboard'))

def login():
    if request.method == 'GET':
        return render_template('login.html')
    email = request.form['email']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("We can't find an account related with this Email id. Please verify the Email entered.", "error")
        return redirect(url_for('login'))
    elif not check_password(password):
        flash("Invalid Password. Please verify the password entered.")
        return redirect(url_for('login'))
    login_user(user, remember = remember_me)
    flash('Logged in successfully')
    return redirect(request.args.get('next') or url_for('dashboard'))


def logout():
    logout_user()
    return redirect(url_for('index'))

@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)
