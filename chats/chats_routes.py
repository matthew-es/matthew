from . import chats
from flask import render_template, redirect, url_for, request, current_app, session

import bleach
import datetime as dt
import os
import re
import requests
import markdown

import common.sockets as sck
import common.apis as api
import common.azure as az
import common.logger as log
import common.database as db
import chats.chats_database as chdb
    
#######################################################################################

def get_distinct_chat_ids():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(chdb.chats_select_all_by_id())
    chat_ids = cursor.fetchall()
    
    cursor.close()
    new_connection.close()
    
    return chat_ids

def get_distinct_prompt_ids():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(chdb.chats_prompts_select_all_all())
    prompt_ids = cursor.fetchall()
    
    cursor.close()
    new_connection.close()
    
    return prompt_ids

#######################################################################################
# /chats/prompts/

@chats.route('/prompts/')
def chats_prompts():
    page_title = "Chat Prompts"
    chat_prompt_ids = get_distinct_prompt_ids()
    return render_template('chats_prompts.html', chat_prompt_ids=chat_prompt_ids, environ=os.environ, page_title=page_title)

@chats.route('/prompts/new/', methods=['GET', 'POST'])
def chats_prompts_new():
    page_title = "New Prompt"
    if request.method == 'POST':
        chat_prompt_title = request.form.get('chat_prompt_title')
        chat_prompt_text = request.form.get('chat_prompt_text')

        # Assuming you have a function to get a DB connection
        new_connection = db.db_connect_open()
        cursor = new_connection.cursor()
        
        cursor.execute(chdb.chats_prompts_insert_new(), (chat_prompt_title, chat_prompt_text))
        
        new_prompt_id = cursor.fetchone()[0]
        
        new_connection.commit()
        cursor.close()
        db.db_connect_close(new_connection)
        
        return redirect(url_for('chats.chats_prompts_view', chat_prompt_id=new_prompt_id))  # Redirect to the same page or to another page as confirmation

    # If not a POST request, just render the form
    return render_template('chats_prompts_new.html', environ=os.environ, page_title=page_title)

@chats.route('/prompts/<int:chat_prompt_id>/', methods=['GET', 'POST'])
def chats_prompts_view(chat_prompt_id):
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()

    if request.method == 'POST':
        # Retrieve updated data from form
        chat_prompt_title = request.form['chat_prompt_title']
        chat_prompt_text = request.form['chat_prompt_text']

        # Update the database
        cursor.execute(chdb.chats_prompts_update(),(chat_prompt_title, chat_prompt_text, chat_prompt_id))
        new_connection.commit()

        # Redirect to avoid form resubmission issues
        return redirect(url_for('chats.chats_prompts'))
    
    
    # For a GET request, or initially for a POST request
    cursor.execute(chdb.chats_prompts_select_by_id(), (chat_prompt_id,))
    chat_prompt_details = cursor.fetchone()
    cursor.close()
    new_connection.close()

    if chat_prompt_details:
        chat_prompt_id, chat_prompt_title, chat_prompt_text = chat_prompt_details
    else:
        chat_prompt_title, chat_prompt_text = None, None

    page_title = f"Edit Prompt: {chat_prompt_title}"
    return render_template('chats_prompts_detail.html', chat_prompt_id=chat_prompt_id, chat_prompt_title=chat_prompt_title, chat_prompt_text=chat_prompt_text, environ=os.environ, page_title=page_title)

############################################################################################################
# /chats/

@chats.route('/')
def index():
    chat_ids = get_distinct_chat_ids()
    page_title = "Chats"
    return render_template('chats.html', chat_ids=chat_ids, environ=os.environ, page_title=page_title)

@chats.route('/new/')
def chat_new():
    page_title = "New Chat"

    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(chdb.chats_prompts_select_all_id_title())
    chat_prompts = cursor.fetchall()
    
    cursor.execute(chdb.chats_llms_select_all_id_title())
    llms = cursor.fetchall()
    
    cursor.close()
    db.db_connect_close(new_connection)
        
    return render_template('chats_new.html', chat_prompts=chat_prompts, llms=llms, environ=os.environ, page_title=page_title)

@sck.socketio.on('ask_question')
def handle_question(data):
    try:
        # There is a user who wants to chat
        user_id = 'b79cb3ba-745e-5d9a-8903-4a02327a7e09'
        
        # First, grab the form variables via sockets
        question = data['question']
        chat_prompt_id = data['chat_prompt_id'] 
        llm_id = data['llm_id']
        log.log_message(f"QUESTION: {question}")
        log.log_message(f"PROMPT ID: {chat_prompt_id}")
        log.log_message(f"LLM MODEL ID: {llm_id}")
        
        # LLM model and encoding for counting tokens
        # encoding = tt.encoding_for_model(using_llm_model)
        
        # Connection one: stuff before the api call
        chat_connection_one = db.db_connect_open()
        cursor = chat_connection_one.cursor()

        # Deal with the LLM model
        cursor.execute(chdb.chats_llms_select_title_by_id(), (llm_id,))
        llm_title = cursor.fetchone()[0]
        log.log_message(f"LLM MODEL TITLE: {llm_title}")
        
        # Deal with the prompt                 
        cursor.execute(chdb.chats_prompts_select_one_title_text(), (chat_prompt_id,))
        chat_prompt = cursor.fetchall()
        chat_prompt_title = chat_prompt[0][0]
        chat_prompt = chat_prompt[0][1]
    
        log.log_message(f"PROMPT TITLE: {chat_prompt_title}: {chat_prompt[:50]}")
        
        # CONTEXT WINDOW: Have we got a session with a chat already or not?
        if 'chat' not in session:
            session['chat'] = [{
                "role": "system", 
                "content": chat_prompt
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
        # tokens_in_chat = (len(encoding.encode(chat_string)))
        
        # RECORD: Have we got an existing chat in the database or not?
        chat_prompt_text = session['chat'][0]['content'].strip()  
        if 'chat_id' not in session: 
            cursor.execute(chdb.chats_insert_new(),(user_id, llm_id, llm_title, chat_prompt_id, chat_prompt_title, chat_prompt_text))
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
        cursor.execute(chdb.chats_messages_insert_question(),(chat_id, user_id, question))
        
        chat_connection_one.commit()
        cursor.close()
        db.db_connect_close(chat_connection_one)
        
        log.log_message(f"SESSION CHAT ID: {session['chat_id']}")
        chat_characters = ' '.join(message['content'] for message in session['chat'])
        log.log_message(f"SESSION CHAT WITH NEW QUESTION LENGTH: {len(chat_characters)}")
        log.log_message(f"SESSION CHAT WITH NEW QUESTION FOR API: {session['chat']}")
        
        # Now do the API call to one of the LLMs
        answer = ""
        
        openai_models = ["gpt-4-turbo-2024-04-09", "gpt-4-0125-preview", "gpt-3.5-turbo-0125"]
        anthropic_models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]

        # Open AI API
        if llm_title in openai_models:
            try:
                response = api.openai.chat.completions.create(
                    model=llm_title,
                    response_format={"type": "text"},
                    messages=session['chat'],
                    stream=True,
                    temperature=1,
                    max_tokens=2000,
                )
            except Exception as e:
                log.log_message(f"OPENAI ERROR: {e}")

            for chunk in response:
                new_chunk = chunk.choices[0].delta.content
                
                if new_chunk:
                    sck.socketio.emit('new_chunk', {'chunk': new_chunk})
                    answer += new_chunk
                    print(new_chunk)
                elif new_chunk is None and len(answer) > 1:
                    print("STREAM END NOW")
                    sck.socketio.emit('stream_end')
        
        # Anthropic API
        if llm_title in anthropic_models:
            try:
                response = api.anthropic.Anthropic().messages.create(
                    model=llm_title,
                    system=session['chat'][0]['content'],
                    messages=session['chat'][1:],
                    stream=True,
                    temperature=1.0,
                    max_tokens=2000,
                )
            except Exception as e:
                log.log_message(f"ANTHROPIC ERROR: {e}")
            
            for chunk in response:
                if chunk.type == "content_block_delta":
                    new_chunk = chunk.delta.text
                    print(new_chunk)
                    sck.socketio.emit('new_chunk', {'chunk': new_chunk})
                    answer += new_chunk
                elif chunk.type == "message_stop":
                    print("STREAM END NOW")
                    sck.socketio.emit('stream_end')
        
        # Now deal with the complete answer for the context window and the database record
        if answer is not None:
            # log.log_message(repr(answer))
            session['chat'].append({"role": "assistant", "content": answer})
            session.modified = True
            
            # Database connection two: after the API call stuff
            chat_connection_two = db.db_connect_open()
            cursor = chat_connection_two.cursor()
            cursor.execute(chdb.chats_messages_insert_answer(),(chat_id, user_id, answer))
            chat_connection_two.commit()
            cursor.close()
            db.db_connect_close(chat_connection_two)
            

        chat_characters = ' '.join(message['content'] for message in session['chat'])
        log.log_message(f"SESSION WHOLE CHAT AT END LENGTH: {len(chat_characters)}")
        log.log_message(f"SESSION WHOLE CHAT AT END: {session['chat']}")
        return ('', 204)
    except Exception as e:
        log.log_message(f"Error in /ask: {e}")
        sck.socketio.emit('error', {'message': 'An XXX error occurred'}) 
        # return "An error occurred", 500

@chats.route('/<int:chat_id>/')
def view_chat(chat_id):
    page_title = f"Chat Nº {chat_id}"
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(chdb.chats_messages_select_all_by_chat_id(), (chat_id,))
    raw_messages = cursor.fetchall() 
    messages = [(bleach.clean(
        markdown.markdown(message, extensions=['fenced_code']),
        tags=current_app.config['BLEACH_ALLOWED_TAGS'],
        attributes=current_app.config['BLEACH_ALLOWED_ATTRIBUTES']
        # , strip=True
        ), status) for message, status in raw_messages]

    cursor.execute(chdb.chats_select_details_by_chat_id(), (chat_id,))
    chat_details = cursor.fetchone()
    
    cursor.close()
    new_connection.close()
    
    if chat_details:
        llm_title, chat_prompt_id, chat_prompt_title, chat_prompt_text = chat_details
    else:
        llm_title, chat_prompt_id, chat_prompt_title, chat_prompt_text = None, None, None, None
    
    return render_template('chats_detail.html', llm_title=llm_title, chat_prompt_id=chat_prompt_id, chat_prompt_title=chat_prompt_title, chat_prompt_text=chat_prompt_text, messages=messages, environ=os.environ, page_title=page_title) 


@chats.route('/reset/')
def reset():
    # Remove the value from the session
    session.clear()
    return 'All reset.'

@chats.route('/reset_streaming_answer/')
def reset_streaming_answer():
    # Remove the value from the session
    session.pop('chat_history', None)
    return 'All reset.'


# #######################################################################################
# #  OLD VERSION Chats

# def stream():
#     def generate():
#         if session.get('chat_history') is None:
#             return
#         else:
#             while session['chat_history']:
#                 yield f"data: {session['chat_history'].pop(0)}\n\n"
#                 session.modified = True

#     return Response(stream_with_context(generate()), content_type='text/event-stream')