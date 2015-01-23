from flask import request, flash, url_for, render_template, redirect, jsonify
from flask.ext.login import LoginManager, login_user, logout_user, current_user, login_required
from formspree.utils import request_wants_json, jsonerror
from sqlalchemy.exc import IntegrityError
from formspree import settings
from helpers import check_password
from formspree.app import DB
from models import User
from formspree.forms.models import Form

def register():
    if request.method == 'GET':
        return render_template('users/register.html')
    try:
        user = User(request.form['email'], request.form['password'])
        DB.session.add(user)
        DB.session.commit()

    except IntegrityError:
        DB.session.rollback()
        flash("An account with this email already exists.", "error")
        return render_template('users/register.html')

    login_user(user)
    flash('Your account is successfully registered.')

    return redirect(url_for('dashboard'))

def login():
    if request.method == 'GET':
        return render_template('users/login.html')
    email = request.form['email']
    password = request.form['password']
    remember_me = False
    if 'remember_me' in request.form:
        remember_me = True
    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("We can't find an account related with this Email id. Please verify the Email entered.", "error")
        return redirect(url_for('login'))
    elif not check_password(user.password, password):
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
    return render_template('users/dashboard.html', user=current_user)

@login_required
def forms():
    if request.method == 'GET':
        if request_wants_json():
            return jsonerror(501, {'error': "This endpoint may return the list of forms for the logged user."})
        else:
            return redirect(url_form('dashboard'))

    # Create a new form
    if not current_user.upgraded:
        return jsonerror(403, {'error': "Please upgrade your account."})

    email = request.get_json().get('email') or abort(400)
    form = Form(email, owner=current_user)
    DB.session.add(form)
    DB.session.commit()

    # A unique identifier for the form that maps to its id,
    # but doesn't seem like a sequential integer
    random_like_string = form.get_random_like_string()

    return jsonify({
        'ok': True,
        'random_like_string': random_like_string,
        'submission_url': settings.API_ROOT + '/' + random_like_string
    })
