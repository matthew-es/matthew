from flask import Flask, Response, stream_with_context, render_template, request, session, redirect, url_for, jsonify, flash
from flask_session import Session
from flask_socketio import SocketIO, emit

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

import openai as ai
import tiktoken as tt
import anthropic

import matthew_logger as log
import matthew_database as db

#######################################################################################
# Flask app stuff, ENV variables, sessions, sockets

app = Flask(__name__)
dotenv.load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app)


#######################################################################################
# Connect to APIs

ai.api_key = os.getenv("OPENAI_API_KEY")


#######################################################################################
# DATABASE STUFF

new_connection = db.db_connect_open()
db.check_or_create_tables(new_connection)
# db.udpates_tables(new_connection)
db.db_connect_close(new_connection)

@app.route('/')
def index():
    log.log_message("INDEX PAGE")
    return render_template('index.html')

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

def get_distinct_chat_ids():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute("SELECT chatid FROM matthew_chats ORDER BY chatid")
    chat_ids = cursor.fetchall()
    
    cursor.close()
    new_connection.close()
    
    return chat_ids

def get_distinct_prompt_ids():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute("SELECT promptid, prompttitle, prompttext FROM matthew_chatprompts ORDER BY promptid")
    prompt_ids = cursor.fetchall()
    
    cursor.close()
    new_connection.close()
    
    return prompt_ids


#######################################################################################
# Prompts

@app.route('/dcx/prompts/')
def prompts():
    page_title = "Prompts"
    prompt_ids = get_distinct_prompt_ids()
    return render_template('prompts.html', prompt_ids=prompt_ids, environ=os.environ, page_title=page_title)

@app.route('/dcx/prompt/new', methods=['GET', 'POST'])
def prompt_new():
    page_title = "New Prompt"
    if request.method == 'POST':
        prompt_title = request.form.get('prompttitle')
        prompt_text = request.form.get('prompttext')

        # Assuming you have a function to get a DB connection
        new_connection = db.db_connect_open()
        cursor = new_connection.cursor()
        
        cursor.execute("""
            INSERT INTO matthew_chatprompts (prompttitle, prompttext) 
            VALUES (%s, %s)
            RETURNING promptid
        """, (prompt_title, prompt_text))
        
        new_prompt_id = cursor.fetchone()[0]
        
        new_connection.commit()
        cursor.close()
        db.db_connect_close(new_connection)
        
        return redirect(url_for('view_prompt', prompt_id=new_prompt_id))  # Redirect to the same page or to another page as confirmation

    # If not a POST request, just render the form
    return render_template('prompt_new.html', environ=os.environ, page_title=page_title)

@app.route('/dcx/prompts/<int:prompt_id>', methods=['GET', 'POST'])
def view_prompt(prompt_id):
    page_title = "Edit Prompt"
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()

    if request.method == 'POST':
        # Retrieve updated data from form
        prompt_title = request.form['prompttitle']
        prompt_text = request.form['prompttext']

        # Update the database
        cursor.execute(
            "UPDATE matthew_chatprompts SET prompttitle = %s, prompttext = %s, updatedat = CURRENT_TIMESTAMP WHERE promptid = %s",
            (prompt_title, prompt_text, prompt_id)
        )
        new_connection.commit()

        # Redirect to avoid form resubmission issues
        return redirect(url_for('prompts'))
    
    # For a GET request, or initially for a POST request
    cursor.execute(
        "SELECT promptid, prompttitle, prompttext FROM matthew_chatprompts WHERE promptid = %s",
        (prompt_id,)
    )
    prompt_details = cursor.fetchone()
    cursor.close()
    new_connection.close()

    if prompt_details:
        promptid, prompttitle, prompttext = prompt_details
    else:
        prompttitle, prompttext = None, None

    return render_template('prompts_detail.html', promptid=promptid, prompttitle=prompttitle, prompttext=prompttext, environ=os.environ, page_title=page_title)


#######################################################################################
# Chats

@app.route('/dcx/chats/')
def chats():
    chat_ids = get_distinct_chat_ids()
    page_title = "Chats"
    return render_template('chats.html', chat_ids=chat_ids, environ=os.environ, page_title=page_title)

@app.route('/dcx/chats/new')
def chat():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute("SELECT promptid, prompttitle FROM matthew_chatprompts ORDER BY createdat DESC")
    prompts = cursor.fetchall()
    
    cursor.execute("SELECT llmmodelid, llmmodeltitle FROM matthew_llmmodels ORDER BY llmmodeltitle DESC")
    llmmodels = cursor.fetchall()
    
    cursor.close()
    db.db_connect_close(new_connection)
        
    return render_template('chats_new.html', prompts=prompts, llmmodels=llmmodels, environ=os.environ)

@app.route('/dcx/chats/<int:chat_id>')
def view_chat(chat_id):
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(
        "SELECT chatmessagecontent, chatmessagetype FROM matthew_chatmessages WHERE chatid = %s ORDER BY chatmessageid",
        (chat_id,)
    )
    raw_messages = cursor.fetchall() 
    messages = [(bleach.clean(
        markdown.markdown(message, extensions=['fenced_code']),
        tags=app.config['BLEACH_ALLOWED_TAGS'],
        attributes=app.config['BLEACH_ALLOWED_ATTRIBUTES']
        # , strip=True
        ), status) for message, status in raw_messages]

    cursor.execute(
        "SELECT chatmodel, promptid, chatprompttitle, chatprompt FROM matthew_chats WHERE chatid = %s",
        (chat_id,)
    )
    chat_details = cursor.fetchone()
    
    cursor.close()
    new_connection.close()
    
    if chat_details:
        chatmodel, promptid, prompttitle, prompttext = chat_details
    else:
        chatmodel, promptid, prompttitle, prompttext = None, None, None, None
    
    return render_template('chats_detail.html', chatmodel=chatmodel, promptid=promptid, prompttitle=prompttitle, prompttext=prompttext, messages=messages, environ=os.environ)

@app.route('/read')
def read():
    conv = session.get('conversation', None)
    chat = session.get('chat_history', None)
    return jsonify(conversation=conv, chat_history=chat)

@app.route('/reset')
def reset():
    # Remove the value from the session
    session.clear()
    return 'All reset.'

@app.route('/reset_streaming_answer')
def reset_streaming_answer():
    # Remove the value from the session
    session.pop('chat_history', None)
    return 'All reset.'

@app.route('/ask', methods=['POST'])
def ask():
    try:
        print(request.form['prompt_id'])
        print(request.form['llmmodelid'])
        print(request.form['question'])
        
        using_llm_model = "gpt-4-0125-preview"
        encoding = tt.encoding_for_model(using_llm_model)
        
        prompt_id = request.form['prompt_id']
        llmmodelid = request.form['llmmodelid']
        prompt_connection = db.db_connect_open()
        cursor = prompt_connection.cursor()
    
        print("LLM MODEL ID: ", llmmodelid)
        
        cursor.execute("SELECT prompttitle, prompttext FROM matthew_chatprompts WHERE promptid = %s", (prompt_id,))
        prompt = cursor.fetchall()
        if prompt:
            prompttitle = prompt[0][0]
            prompt = prompt[0][1]
        else:
            prompttitle = "No prompt found."
            prompt = "No prompt found."
        
        cursor.execute("SELECT llmmodeltitle FROM matthew_llmmodels WHERE llmmodelid = %s", (llmmodelid,))
        llmmodeltitle = cursor.fetchall()
        
        print("LLM MODEL TITLE: ", llmmodeltitle[0][0])
        
        prompt_connection.commit()
        cursor.close()
        db.db_connect_close(prompt_connection)
                
        if 'conversation' not in session:
            session['conversation'] = [{
                "role": "system", 
                "content": prompt
            }]
            session.modified = True
        
        conversation_string = ' '.join(message['content'] for message in session['conversation'])
        tokens_in_conversation = (len(encoding.encode(conversation_string)))
         
        chat_id = None
        chat_prompt_title = prompttitle
        chat_prompt = session['conversation'][0]['content'].strip()
                
        # Deal with the user's question:
        user_input = request.form['question']
        session['conversation'].append({"role": "user", "content": user_input})
        session.modified = True
        question_connection = db.db_connect_open()
        cursor = question_connection.cursor()
        
        user_id = 'b79cb3ba-745e-5d9a-8903-4a02327a7e09'  # Replace with actual logic to retrieve user UUID
         
        if 'chat_id' not in session: 
            cursor.execute(
                "INSERT INTO matthew_chats (userid, promptid, chatmodel, chatprompttitle, chatprompt) VALUES (%s, %s, %s, %s, %s) RETURNING chatid;",
                (user_id, prompt_id, using_llm_model, chat_prompt_title, chat_prompt)
            )
            chat_id = cursor.fetchone()[0]
            session['chat_id'] = chat_id
            session.modified = True
        else:
            chat_id = session['chat_id']
        
        print("NEW CHAT ID NOW: ", chat_id)
        
        cursor.execute(
            """
            INSERT INTO matthew_chatmessages (chatid, userid, chatmessagecontent, chatmessagetype)
            VALUES (%s, %s, %s, 'question')
            """,
            (chat_id, user_id, user_input)
        )
        
        question_connection.commit()
        cursor.close()
        db.db_connect_close(question_connection)
        
        # Now do the API call to the LLM
        response = ai.chat.completions.create(
            model=using_llm_model,
            response_format={"type": "text"},
            messages=session['conversation'],
            stream=True,
            temperature=1.3,
            max_tokens=300,
        )
        
        # Now deal with the answer from the LLM
        answer = ""
        session['chat_history'] = []

        for chunk in response:
            new_chunk = chunk.choices[0].delta.content
            if new_chunk:
                session['chat_history'].append(new_chunk)
                session.modified = True
                print(new_chunk)
                answer += new_chunk
            elif new_chunk is None and len(answer) > 1:
                session['chat_history'].append(f"<br /><strong>TOKENS:</strong> {tokens_in_conversation}")
                session['chat_history'].append("ENDEND")
                session.modified = True
        
        log.log_message(f"CHAT ID: {chat_id}")
        
        if answer is not None:
            # conversation.append({"role": "assistant", "content": answer})
            session['conversation'].append({"role": "assistant", "content": answer})
            session.modified = True
            
            answer_connection = db.db_connect_open()
            cursor = answer_connection.cursor()
            cursor.execute(
                """
                INSERT INTO matthew_chatmessages (chatid, userid, chatmessagecontent, chatmessagetype)
                VALUES (%s, %s, %s, 'answer')
                """,
                (chat_id, user_id, answer)
            )
            answer_connection.commit()
            cursor.close()
            db.db_connect_close(answer_connection)
            

        # print("CONVERSATION 3: ", conversation)
        log.log_message(f"SESSION END: {session['conversation']}")    
        return ('', 204)  # Return an empty response for the POST request
    except Exception as e:
        log.log_message(f"Error in /ask: {e}")
        return "An error occurred", 500

def stream():
    def generate():
        if session.get('chat_history') is None:
            return
        else:
            while session['chat_history']:
                yield f"data: {session['chat_history'].pop(0)}\n\n"
                session.modified = True

    return Response(stream_with_context(generate()), content_type='text/event-stream')

############################################################################################################
# SocketsIO Chat

@app.route('/dcx/chats/new/sockets')
def chat_sockets():
    page_title = "New Chat"

    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute("SELECT promptid, prompttitle FROM matthew_chatprompts ORDER BY createdat DESC")
    prompts = cursor.fetchall()
    
    cursor.execute("SELECT llmmodelid, llmmodeltitle FROM matthew_llmmodels ORDER BY llmmodeltitle DESC")
    llmmodels = cursor.fetchall()
    
    cursor.close()
    db.db_connect_close(new_connection)
        
    return render_template('chats_new_sockets.html', prompts=prompts, llmmodels=llmmodels, environ=os.environ, page_title=page_title)

@socketio.on('ask_question')
def handle_question(data):
    try:
        # There is a user who wants to chat
        user_id = 'b79cb3ba-745e-5d9a-8903-4a02327a7e09'
        
        # First, grab the form variables via sockets
        question = data['question']
        prompt_id = data['prompt_id'] 
        llmmodelid = data['llmmodelid']
        log.log_message(f"QUESTION: {question}")
        log.log_message(f"PROMPT ID: {prompt_id}")
        log.log_message(f"LLM MODEL ID: {llmmodelid}")
        
        # LLM model and encoding for counting tokens
        using_llm_model = "gpt-4-0125-preview"
        encoding = tt.encoding_for_model(using_llm_model)
        
        # Connection one: stuff before the api call
        chat_connection_one = db.db_connect_open()
        cursor = chat_connection_one.cursor()

        # Deal with the LLM model
        cursor.execute("SELECT llmmodeltitle FROM matthew_llmmodels WHERE llmmodelid = %s", (llmmodelid,))
        llmmodeltitle = cursor.fetchone()[0]
        log.log_message(f"LLM MODEL TITLE: {llmmodeltitle}")
        
        # Deal with the prompt                 
        cursor.execute("SELECT prompttitle, prompttext FROM matthew_chatprompts WHERE promptid = %s", (prompt_id,))
        prompt = cursor.fetchall()
        prompttitle = prompt[0][0]
        prompt = prompt[0][1]
    
        log.log_message(f"PROMPT TITLE: {prompttitle}: {prompt[:50]}")
        
        # CONTEXT WINDOW: Have we got a session with a chat already or not?
        if 'chat' not in session:
            session['chat'] = [{
                "role": "system", 
                "content": prompt
            }]
            session.modified = True
            chat_characters = ' '.join(message['content'] for message in session['chat'])
            log.log_message(f"SESSION (EXISTING) START STATE ON QUESTION LENGTH: {len(chat_characters)}")
            log.log_message(f"NEW CHAT: {session['chat']}")    
        else:
            chat_characters = ' '.join(message['content'] for message in session['chat'])
            log.log_message(f"EXISTING START STATE ON QUESTION LENGTH: {len(chat_characters)}")
            log.log_message(f"EXISTING CHAT: {session['chat']}")
        
        # Character and token counting things
        chat_string = ' '.join(message['content'] for message in session['chat'])
        tokens_in_chat = (len(encoding.encode(chat_string)))
        
        # RECORD: Have we got an existing chat in the database or not?
        chat_prompt = session['chat'][0]['content'].strip()  
        if 'chat_id' not in session: 
            cursor.execute(
                "INSERT INTO matthew_chats (userid, promptid, chatmodel, chatprompttitle, chatprompt) VALUES (%s, %s, %s, %s, %s) RETURNING chatid;",
                (user_id, prompt_id, llmmodeltitle, prompttitle, chat_prompt)
            )
            chat_id = cursor.fetchone()[0]
            session['chat_id'] = chat_id
            session.modified = True
            log.log_message(f"NEW CHAT ID: {chat_id}")
        else:
            chat_id = session['chat_id']
            log.log_message(f"EXISTING CHAT ID: {chat_id}")
        
        # Now we deal with the user's question: append to the session then record in the database:
        session['chat'].append({"role": "user", "content": question})
        session.modified = True
        cursor.execute(
            "INSERT INTO matthew_chatmessages (chatid, userid, chatmessagecontent, chatmessagetype) VALUES (%s, %s, %s, 'question')",
            (chat_id, user_id, question)
        )
        
        chat_connection_one.commit()
        cursor.close()
        db.db_connect_close(chat_connection_one)
        
        log.log_message(f"SESSION CHAT ID: {session['chat_id']}")
        chat_characters = ' '.join(message['content'] for message in session['chat'])
        log.log_message(f"SESSION CHAT WITH NEW QUESTION LENGTH: {len(chat_characters)}")
        log.log_message(f"SESSION CHAT WITH NEW QUESTION FOR API: {session['chat']}")
        
        # Now do the API call to one of the LLMs
        answer = ""
        
        openai_models = ["gpt-4-0125-preview", "gpt-3.5-turbo-0125"]
        anthropic_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]

        # Open AI API
        if llmmodeltitle in openai_models:
            try:
                response = ai.chat.completions.create(
                    model=llmmodeltitle,
                    response_format={"type": "text"},
                    messages=session['chat'],
                    stream=True,
                    temperature=1.3,
                    max_tokens=500,
                )
            except Exception as e:
                log.log_message(f"OPENAI ERROR: {e}")

            for chunk in response:
                new_chunk = chunk.choices[0].delta.content
                
                if new_chunk:
                    # mk_new_chunk = markdown.markdown(new_chunk, extensions=['fenced_code'])
                    # bleach_new_chunk = bleach.clean(new_chunk, tags=app.config['BLEACH_ALLOWED_TAGS'], attributes=app.config['BLEACH_ALLOWED_ATTRIBUTES'])
                    emit('new_chunk', {'chunk': new_chunk}, broadcast=True)
                    answer += new_chunk
                    print(new_chunk)
                elif new_chunk is None and len(answer) > 1:
                    print("STREAM END NOW")
                    emit('stream_end', broadcast=True)
        
        # Anthropic API
        if llmmodeltitle in anthropic_models:
            try:
                response = anthropic.Anthropic().messages.create(
                    model=llmmodeltitle,
                    system=session['chat'][0]['content'],
                    messages=session['chat'][1:],
                    stream=True,
                    temperature=1.0,
                    max_tokens=500,
                )
            except Exception as e:
                log.log_message(f"ANTHROPIC ERROR: {e}")
            
            for chunk in response:
                if chunk.type == "content_block_delta":
                    new_chunk = chunk.delta.text
                    print(new_chunk)
                    emit('new_chunk', {'chunk': new_chunk}, broadcast=True)
                    answer += new_chunk
                elif chunk.type == "message_stop":
                    print("STREAM END NOW")
                    emit('stream_end', broadcast=True)
        
        # Now deal with the complete answer for the context window and the database record
        if answer is not None:
            # log.log_message(repr(answer))
            session['chat'].append({"role": "assistant", "content": answer})
            session.modified = True
            
            # Database connection two: after the API call stuff
            chat_connection_two = db.db_connect_open()
            cursor = chat_connection_two.cursor()
            cursor.execute(
                "INSERT INTO matthew_chatmessages (chatid, userid, chatmessagecontent, chatmessagetype) VALUES (%s, %s, %s, 'answer')",
                (chat_id, user_id, answer)
            )
            chat_connection_two.commit()
            cursor.close()
            db.db_connect_close(chat_connection_two)
            

        chat_characters = ' '.join(message['content'] for message in session['chat'])
        log.log_message(f"SESSION WHOLE CHAT AT END LENGTH: {len(chat_characters)}")
        log.log_message(f"SESSION WHOLE CHAT AT END: {session['chat']}")
        return ('', 204)
    except Exception as e:
        log.log_message(f"Error in /ask: {e}")
        emit('error', {'message': 'An XXX error occurred'}, broadcast=True) 
        # return "An error occurred", 500


############################################################################################################
# RSS

@app.route('/dcx/rss/refresh')
def refresh_rss():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    # Retrieve all RSS feed URLs from the database
    cursor.execute("SELECT rssfeedid, rssfeedurl, rssfeedtitle FROM matthew_rssfeeds")
    feeds = cursor.fetchall()
    
    for feed in feeds:
        rssfeedid, rssfeedurl, rssfeedtitle = feed
        try:
            response = requests.get(rssfeedurl)
            root = ET.fromstring(response.content)
            
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                
                # Before inserting, check if the item already exists to avoid duplicates
                cursor.execute("SELECT COUNT(*) FROM matthew_rssitems WHERE rssitemurl = %s", (link,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        "INSERT INTO matthew_rssitems (rssfeedid, rssitemurl, rssitemtitle, createdat, updatedat) VALUES (%s, %s, %s, %s, %s)",
                        (rssfeedid, link, title, dt.datetime.now(), dt.datetime.now())
                    )
        except Exception as e:
            print(f"Failed to process feed {rssfeedurl}: {e}")
    
    new_connection.commit()
    cursor.close()
    db.db_connect_close(new_connection)
    
    # Redirect back to the RSS display page
    return redirect(url_for('rss'))

@app.route('/dcx/rss')
def rss():
    page_title = "RSS"
    chat_ids = get_distinct_chat_ids()
    
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(
        """
        SELECT r.rssitemtitle, r.rssitemurl, f.rssfeedtitle, r.createdat 
        FROM matthew_rssitems r
        JOIN matthew_rssfeeds f ON r.rssfeedid = f.rssfeedid
        ORDER BY r.createdat DESC
        """
    )
    items = cursor.fetchall()
    
    for i, item in enumerate(items):
        items[i] = item[:3] + (item[3].strftime('%b %d %H:%M'),)
    
    cursor.close()
    db.db_connect_close(new_connection)
    
    return render_template('rss.html', items=items, chat_ids=chat_ids, environ=os.environ, page_title=page_title)

############################################################################################################
# Users

class SignupForm(fwtf.FlaskForm):
    email = wtf.StringField('Email', validators=[wtf.validators.DataRequired(), wtf.validators.Email()])
    submit = wtf.SubmitField('Sign Up')

@app.route('/dcx/signup', methods=['GET', 'POST'])
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


#######################################################################################

if __name__ == '__main__':
    socketio.run(app, debug=True)