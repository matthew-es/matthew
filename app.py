from flask import Flask, Response, stream_with_context, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
import os
import dotenv
import time
import datetime as dt
import requests
import xml.etree.ElementTree as ET

import openai as ai
import tiktoken as tt

import matthew_logger as log
import matthew_database as db

#######################################################################################
# Setup stuff

app = Flask(__name__)
dotenv.load_dotenv()
ai.api_key = os.getenv("OPENAI_API_KEY")
app.secret_key = 'your_secret_key_123'

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


#######################################################################################
# OPEN DATABASE CONNECTION
new_connection = db.db_connect_open()
db.check_or_create_tables(new_connection)
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
    prompt_ids = get_distinct_prompt_ids()
    return render_template('prompts.html', prompt_ids=prompt_ids, environ=os.environ)

@app.route('/dcx/prompt/new', methods=['GET', 'POST'])
def prompt_new():
    if request.method == 'POST':
        prompt_title = request.form.get('prompttitle')
        prompt_text = request.form.get('prompttext')

        # Assuming you have a function to get a DB connection
        new_connection = db.db_connect_open()
        cursor = new_connection.cursor()
        
        cursor.execute("""
            INSERT INTO matthew_chatprompts (prompttitle, prompttext) 
            VALUES (%s, %s)
        """, (prompt_title, prompt_text))
        
        new_connection.commit()
        cursor.close()
        db.db_connect_close(new_connection)
        
        return redirect(url_for('prompt_new'))  # Redirect to the same page or to another page as confirmation

    # If not a POST request, just render the form
    return render_template('prompt_new.html', environ=os.environ)

@app.route('/dcx/prompts/<int:prompt_id>', methods=['GET', 'POST'])
def view_prompt(prompt_id):
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
        return redirect(url_for('view_prompt', prompt_id=prompt_id))
    
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

    return render_template('prompts_detail.html', promptid=promptid, prompttitle=prompttitle, prompttext=prompttext, environ=os.environ)


#######################################################################################
# Chats

@app.route('/dcx/chats/')
def chats():
    chat_ids = get_distinct_chat_ids()
    return render_template('chats.html', chat_ids=chat_ids, environ=os.environ)

@app.route('/dcx/chats/new')
def chat():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    cursor.execute("SELECT promptid, prompttitle FROM matthew_chatprompts ORDER BY createdat DESC")
    prompts = cursor.fetchall()
    cursor.close()
    db.db_connect_close(new_connection)
    
    for prompt in prompts:
        log.log_message(prompt)
    
    return render_template('chats_new.html', prompts=prompts, environ=os.environ)

@app.route('/dcx/chats/<int:chat_id>')
def view_chat(chat_id):
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(
        "SELECT chatmessagecontent, chatmessagetype FROM matthew_chatmessages WHERE chatid = %s ORDER BY chatmessageid",
        (chat_id,)
    )
    messages = cursor.fetchall() 
    
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
        using_llm_model = "gpt-4-0125-preview"
        encoding = tt.encoding_for_model(using_llm_model)
        
        prompt_id = request.form['prompt_id']
        prompt_connection = db.db_connect_open()
        cursor = prompt_connection.cursor()
        
        cursor.execute("SELECT prompttitle, prompttext FROM matthew_chatprompts WHERE promptid = %s", (prompt_id,))
        prompt = cursor.fetchall()
        if prompt:
            prompttitle = prompt[0][0]
            prompt = prompt[0][1]
        else:
            prompttitle = "No prompt found."
            prompt = "No prompt found."
        
        prompt_connection.commit()
        cursor.close()
        db.db_connect_close(prompt_connection)
        
        print(f"Prompt: {prompt}")
        print(f"Prompt Title: {prompttitle}")
        print(f"Prompt Text: {prompt}")
        
        if 'conversation' not in session:
            session['conversation'] = [{
                "role": "system", 
                "content": prompt
            }]
            session.modified = True
        
        conversation_string = ' '.join(message['content'] for message in session['conversation'])
        tokens_in_conversation = (len(encoding.encode(conversation_string)))
        print(f"Tokens in conversation: {tokens_in_conversation}")
         
        chat_id = None
        chat_prompt_title = prompttitle
        chat_prompt = session['conversation'][0]['content'].strip()
        
        print("CHAT PROMPT TITLE: ", chat_prompt_title)
        print ("CHAT PROMPT: ", chat_prompt)
        
        # Deal with the user's question:
        user_input = request.form['question']
        session['conversation'].append({"role": "user", "content": user_input})
        session.modified = True
        question_connection = db.db_connect_open()
        cursor = question_connection.cursor()
        
        user_id = 'b79cb3ba-745e-5d9a-8903-4a02327a7e09'  # Replace with actual logic to retrieve user UUID
        
        print("USER INPUT: ", user_input)
        print("USER ID: ", user_id)
        print("CONVERSATION 2: ", session['conversation'])
        print("CHAT ID: ", chat_id)
        
        if 'chat_id' not in session:
            print("NO CHAT ID SO INSERTING INTO DATABASE")
            print("USER ID: ", user_id)
            print("PROMPT ID: ", prompt_id)
            print("USING LLM MODEL: ", using_llm_model)
            print("CHAT PROMPT TITLE: ", chat_prompt_title)
            print("CHAT PROMPT: ", chat_prompt) 
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
            max_tokens=200,
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

@app.route('/stream')
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
    
    return render_template('rss.html', items=items, chat_ids=chat_ids, environ=os.environ)

############################################################################################################

if __name__ == '__main__':
    app.run(debug=True)