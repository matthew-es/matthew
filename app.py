from flask import Flask, Response, stream_with_context, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
import os
import dotenv
import time
import requests
import xml.etree.ElementTree as ET

import matthew_logger as log

import openai as ai
import tiktoken as tt

# Setup stuff
app = Flask(__name__)
dotenv.load_dotenv()
ai.api_key = os.getenv("OPENAI_API_KEY")
app.secret_key = 'your_secret_key_123'

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

@app.route('/')
def index():
    log.log_message("INDEX PAGE")
    return render_template('index.html')

@app.route('/dcx/chat')
def chat():
    return render_template('chat.html', environ=os.environ)

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

#######################################################################################

@app.route('/ask', methods=['POST'])
def ask():
    using_llm_model = "gpt-4-0125-preview"
    encoding = tt.encoding_for_model(using_llm_model)
    
    print("MODEL: ", using_llm_model)
    print("ENCODING: ", encoding)
    
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "system", 
            "content": """
                You are Anna, a Commodity Trading Advisor at DCX (www.dcx.group), specialising in agricultural commodities. Known for your succinct advice, you cater specifically to industry insiders, offering insights into trading, logistics, finance, and legal matters. Your responses should be:

Be Direct and Specific: Address queries with straightforward, actionable advice. Focus on the export/import of commodities, providing specifics rather than generalities.

Limited length: unless the user requests for specifics, more information and/or details, reply with maximum 75 words, forcing yourself to be extremely concise without many details

Utilize Expertise: 
Share insights based on your deep understanding of the field, citing authoritative sources (e.g., DGFT, SFA) when relevant. Include direct links for immediate reference.

Network Connections: Offer direct connections within the DCX network pertinent to the user's specific needs in commodity trading.

Clarity in Communication: Use clear British English, aiming for simplicity and directness without sacrificing informativeness.

Regulatory and Logistics Focus: Center your advice on regulatory compliance, freight, and logistics, where DCX can add value, avoiding market insights unless explicitly requested.

Concise Closing: End with a concise question related to the user's next steps in their export/import journey, inviting further detail where necessary.

Brevity: Keep responses succinct, focusing only on the most relevant details for informed decision-making. 

Use the "Signed Up to DCX" file for background information without disclosing company names, focusing instead on their industry and needs to provide relevant advice. 

Respond authoritatively, driving users to optimize their use of DCX platforms. 

For further support, direct users to DCX's customer service at support@dcx.group.
            """
        }]
        session.modified = True
    
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
        max_tokens=200,
    )
    
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
    
    if answer is not None:
        # conversation.append({"role": "assistant", "content": answer})
        session['conversation'].append({"role": "assistant", "content": answer})
        session.modified = True

    # print("CONVERSATION 3: ", conversation)
    print("SESSION END: ", session['conversation'])    
    return ('', 204)  # Return an empty response for the POST request

@app.route('/stream')
def stream():
    def generate():
        if session.get('chat_history') is None:
            return
        else:
            while session['chat_history']:
                yield f"data: {session['chat_history'].pop(0)}\n\n"
                session.modified = True
                time.sleep(0.005)  # Slow down the stream for demonstration

    return Response(stream_with_context(generate()), content_type='text/event-stream')

############################################################################################################

@app.route('/rss')
def rss():
    # List of RSS feed URLs you want to read
    feeds = [
        {'name': 'WSJ Markets', 'url': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml'},
        {'name': 'S&P Commodities', 'url': 'https://www.spglobal.com/commodityinsights/en/rss-feed/agriculture'},
        {'name': 'FT Commodities', 'url': 'https://www.ft.com/commodities?format=rss'},
        {'name': 'BBC Business', 'url': 'http://feeds.bbci.co.uk/news/business/rss.xml'},
        {'name': 'Hindu Agri', 'url': 'https://www.thehindu.com/business/agri-business/feeder/default.rss'},
        {'name': 'WE News', 'url': 'https://en.wenews.pk/feed/'},
        {'name': 'FAO Asia', 'url': 'https://www.fao.org/asiapacific/news/rss/en/'},
        {'name': 'UN Asia', 'url': 'https://news.un.org/feed/subscribe/en/news/region/asia-pacific/feed/rss.xml'}
    ]
    
    items = []
    for feed in feeds:
        try:
            # Fetching the feed
            response = requests.get(feed['url'])
            # Parsing the feed
            root = ET.fromstring(response.content)
            
            # Extracting items (articles) from the feed
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                items.append({'title': title, 'link': link, 'source': feed['name']})
        except Exception as e:
            print(f"Failed to process feed {feed['url']}: {e}")

    # Rendering the items to a simple HTML template
    return render_template('rss.html', items=items)

############################################################################################################

if __name__ == '__main__':
    app.run(debug=True)