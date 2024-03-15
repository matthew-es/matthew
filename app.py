from flask import Flask, Response, stream_with_context, render_template, request, session, redirect, url_for
import os
import dotenv
import time

import openai as ai
import tiktoken as tt

# Setup stuff
app = Flask(__name__)
dotenv.load_dotenv()
ai.api_key = os.getenv("OPENAI_API_KEY")
app.secret_key = 'your_secret_key_123'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dcx/chat')
def chat():
    return render_template('chat.html')

@app.route('/read')
def read():
    value = session.get('conversation', 'Session value not found')
    return render_template('read.html', value=value)

@app.route('/reset')
def reset():
    # Remove the value from the session
    session.pop('conversation', None)
    return 'Session value reset.'

#######################################################################################

chat_history = []

@app.route('/ask', methods=['POST'])
def ask():
    using_llm_model = "gpt-4-0125-preview"
    encoding = tt.encoding_for_model(using_llm_model)
    
    print("MODEL: ", using_llm_model)
    print("ENCODING: ", encoding)
    
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "system", 
            "content": "You are an angry boss called Jerk. You always respond aggressively..."
        }]
    
    conversation_string = ' '.join(message['content'] for message in session['conversation'])
    tokens_in_conversation = (len(encoding.encode(conversation_string)))
    print(f"Tokens in conversation: {tokens_in_conversation}")
    
    user_input = request.form['question']
    # conversation.append({"role": "user", "content": user_input})
    session['conversation'].append({"role": "user", "content": user_input})
    session.modified = True
    
    response = ai.chat.completions.create(
        model=using_llm_model,
        response_format={"type": "text"},
        messages=session['conversation'],
        stream=True,
        temperature=1.3,
        max_tokens=100,
    )
    
    answer = ""

    for chunk in response:
        new_chunk = chunk.choices[0].delta.content
        if new_chunk:
            chat_history.append(new_chunk)
            print(new_chunk)
            answer += new_chunk
        elif new_chunk is None and len(answer) > 1:
            chat_history.append(f"<br /><strong>TOKENS:</strong> {tokens_in_conversation}")
            chat_history.append("ENDEND")
    
    if answer is not None:
        # conversation.append({"role": "assistant", "content": answer})
        session['conversation'].append({"role": "assistant", "content": answer})
        session.modified = True  # Inform Flask that the session has been modified

    # print("CONVERSATION 3: ", conversation)
    print("SESSION END: ", session['conversation'])    
    return ('', 204)  # Return an empty response for the POST request


@app.route('/stream')
def stream():
    def generate():
        while chat_history:
            yield f"data: {chat_history.pop(0)}\n\n"
            time.sleep(0.01)  # Slow down the stream for demonstration
            
    return Response(stream_with_context(generate()), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True)