from flask import Flask, Response, stream_with_context, render_template, request, session, redirect, url_for, jsonify, flash
from flask_session import Session

from markupsafe import Markup
import flask_wtf as fwtf
import wtforms as wtf
import bleach
import markdown

import os
import dotenv
import time
import datetime as dt
import requests
import xml.etree.ElementTree as ET
import re


#######################################################################################
# Flask app, ENV variables, sessions

app = Flask(__name__)
dotenv.load_dotenv()
print("Loaded Connection String:", os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


#######################################################################################
# Common
import common.logger as log
import common.database as db
import common.sockets as sck
sck.socketio.init_app(app)


#######################################################################################
# Blueprints

app.config['TABLE_PREFIX'] = 'matthew'

import users
import users.users_database as usdb
with app.app_context():
    usdb.check_or_create_tables()
app.register_blueprint(users.users, url_prefix='/users')

import rss
import rss.rss_database as rssdb
with app.app_context():
    rssdb.check_or_create_tables()
app.register_blueprint(rss.rss, url_prefix='/rss')

import articles
import articles.articles_database as artdb
with app.app_context():
    artdb.check_or_create_tables()
app.register_blueprint(articles.articles, url_prefix='/articles')

import llms
import llms.llms_database as llmdb
with app.app_context():
    llmdb.check_or_create_tables()
app.register_blueprint(llms.llms, url_prefix='/llms')

import chats
import chats.chats_database as chdb
with app.app_context():
    chdb.check_or_create_tables()
app.register_blueprint(chats.chats, url_prefix='/chats')


#######################################################################################
# DATABASE STUFF


db.check_or_create_tables()

log_file_path = 'matthew_log.txt'  # Update this path
@app.route('/logs')
def show_logs():
    try:
        with open(log_file_path, 'r') as file:
            content = file.read()
        return Response(content, mimetype='text/plain')
    except FileNotFoundError:
        return "Log file not found.", 404


#######################################################################################
# Bleach for html sanitization

app.config['BLEACH_ALLOWED_TAGS'] = list(bleach.sanitizer.ALLOWED_TAGS) + ['p', 'span', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'hr', 'em', 'u', 's', 'ol', 'ul', 'li', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'pre', 'code', 'blockquote']
app.config['BLEACH_ALLOWED_ATTRIBUTES'] = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    'span': ['style'],
    'p': ['style'],
    '*': ['class'],  # Allows the 'class' attribute on all tags
    'div': ['class', 'id'],
    'pre': ['class'],  # Allows class attributes for <pre> for styling purposes
    'code': ['class'], 
}


#######################################################################################
# Common template strings
@app.context_processor
def inject_site_values():
    return {
        'site_name': "Matthew.es",
        'site_description': "Matthew Bennett.",
        'site_keywords': "ai, language, coding, business strategy",
        'site_logo': f"{url_for('static', filename='images/dcx-bull.png')}",
        'site_twitter_name': 'matthewbennett',
        'site_linkedin_name': 'matthewbennett',
        'site_facebook_name': 'matthewbennett',
        'site_email': 'm@matthew.es'
    }

#######################################################################################
# Admin routes

@app.route('/admin/')
def admin():
    page_title = "Admin"
    return render_template('admin.html', environ=os.environ, page_title=page_title)

@app.route('/read')
def read():
    conv = session.get('conversation', None)
    chat = session.get('chat_history', None)
    return jsonify(conversation=conv, chat_history=chat)


#######################################################################################
# Homepage

@app.route('/')
def index():
    page_title = "Matthew.es"
    return render_template('index.html', environ=os.environ, page_title=page_title)


############################################################################################################

if __name__ == '__main__':
    sck.socketio.run(app, debug=True)