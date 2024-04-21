from . import users
from flask import render_template, redirect, url_for, request, flash

import bleach
import datetime as dt
import os
import re
import requests
import markdown

from markupsafe import Markup
import flask_wtf as fwtf
import wtforms as wtf

import common.sockets as sck
import common.apis as api
import common.azure as az
import common.logger as log
import common.database as db
import users.users_database as usdb

############################################################################################################

@users.route('/')
def index(): 
    page_title = "Users Index"

class SignupForm(fwtf.FlaskForm):
    email = wtf.StringField('Email', validators=[wtf.validators.DataRequired(), wtf.validators.Email()])
    submit = wtf.SubmitField('Sign Up')

@users.route('/signup/', methods=['GET', 'POST'])
def signup():
    page_title = "Sign Up"
    form = SignupForm()
    
    if request.method == 'POST':
        email = bleach.clean(form.email.data)

        if form.validate_on_submit():
            signup_success = f'Well done, <strong>{email}</strong>..! Check your inbox (or spam folder) now for your confirmation code.'
            flash(Markup(signup_success), 'success')
            log.log_message(f"NEW EMAIL IS: {email}")
        else:
            for fields, errors in form.errors.items():
                for error in errors:
                    flash(f"Error: {error}", 'error')
        
    return render_template('users_signup.html', form=form, environ=os.environ, page_title=page_title)