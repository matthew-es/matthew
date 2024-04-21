from . import rss
from flask import render_template, redirect, url_for, request, jsonify, request, abort
from markupsafe import Markup, escape
import threading as th

import bleach
import datetime as dt

from dateutil import parser as dup
from dateutil.tz import tzutc as dutz

import os
import re
import requests
import xml.etree.ElementTree as ET

import common.sockets as sck
import common.apis as api
import common.logger as log
import common.database as db
import rss.rss_database as rssdb

#############################################################################################################

def fetch_feed_title(rss_feed_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    
    try:
        response = requests.get(rss_feed_url, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses

        # Parse the XML content
        root = ET.fromstring(response.content)

        # Determine if feed is RSS or Atom
        if root.tag == '{http://www.w3.org/2005/Atom}feed':
            title_tag = '{http://www.w3.org/2005/Atom}title'
        else:
            title_tag = 'title'
        
        # Find the title tag and return its text
        title_element = root.find('.//' + title_tag)
        if title_element is not None:
            return title_element.text
        else:
            return None

    except ET.ParseError as e:
        print(f"XML parsing failed for feed {rss_feed_url}: {e}")
    except requests.HTTPError as e:
        print(f"HTTP request failed for feed {rss_feed_url}: {e}")
    except requests.RequestException as e:
        print(f"HTTP request exception for feed {rss_feed_url}: {e}")
    except Exception as e:
        print(f"Unexpected error when processing feed {rss_feed_url}: {e}")
    return None

@sck.socketio.on('analyse_headline')
def analyse_headline(story):
    print("INSIDE ANALYSE HEADLINE")
#    print("REQUEST: ", request.json)
#    headline = request.json['headline']
    headline = story['headline']
    description = story['description']
    
    print("HEADLINE: ", headline)
    print("DESCRIPTION: ", description)
    
    prompt = [{
        "role": "system",
        "content": """
            You are a news analyst. Analyse this headline with all your contextual knowledge of the world.
            Be decisive. Be insightful. Be accurate. Be direct. Be informative. Be engaging. Be relevant.
            Do not mention "the headline" directly in your response.
            Do not produce a list: just two short paragraphs with normal sentences.
            Highlight one important short keyword phrase in each paragraph in bold.
            Return a maximum of 150 words or 200 tokens.
            """
    },
    {
        "role": "user",
        "content": headline + description
    
    }]
  
    response = api.openai.chat.completions.create(
                    model="gpt-4-turbo-2024-04-09",
                    response_format={"type": "text"},
                    messages=prompt,
                    stream=True,
                    temperature=1,
                    max_tokens=200,
                )
    
    answer = ""    
    for chunk in response:        
        new_chunk = chunk.choices[0].delta.content
        
        if new_chunk:
            sck.socketio.emit('new_chunk', {'chunk': new_chunk})
            answer += new_chunk
            print(new_chunk)
        elif new_chunk is None and len(answer) > 1:
            print("STREAM END NOW")
            sck.socketio.emit('stream_end')    

    return "Success", 200


@rss.route('/feeds/', methods=['GET', 'POST'])
def rss_feeds():
    if request.method == 'POST':
        rss_feed_url = request.form['rss_feed_url']
        rss_feed_title = fetch_feed_title(rss_feed_url)
        
        if rss_feed_title:            
            new_connection = db.db_connect_open()
            cursor = new_connection.cursor()
            cursor.execute(rssdb.rss_feeds_insert_new(), (rss_feed_title, rss_feed_url))
            new_connection.commit()
            cursor.close()
            db.db_connect_close(new_connection)
            
            return redirect(url_for('rss.rss_feeds'))
        else:
            return "Failed to fetch or parse the RSS feed", 400            

    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(rssdb.rss_feeds_select_all())
    rss_feeds = cursor.fetchall()
    rss_feeds = [{
            'id': feed[0],
            'title': feed[1],
            'url': feed[2]
        } for feed in rss_feeds]
    
    cursor.close()
    db.db_connect_close(new_connection)
        
    return render_template('rss_feeds.html', rss_feeds=rss_feeds, environ = os.environ)

def format_date_from_timestamp(unix_timestamp):
    today = dt.datetime.now().date()

    date_time = dt.datetime.fromtimestamp(unix_timestamp)

    if date_time.date() == today:
        # 'I' for 12-hour format without leading zero, 'M' for minutes, 'p' lowercased
        return date_time.strftime('%I:%M %p').lower()
    else:
        # Day/Month/Year format
        return date_time.strftime('%d/%m/%Y')

@rss.route('/')
def index(): 
    page_title = "News"
     
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(rssdb.rss_items_select_all())
    items_list = cursor.fetchall()
    
    items = [{
        'title': item[0],
        'link': item[1],
        'feed': item[2],
        'image': item[3],
        'description': item[4],
        'date': format_date_from_timestamp(item[5]) if item[5] is not None else 'No Date'
    }
    for item in items_list
            ]
    
    cursor.close()
    db.db_connect_close(new_connection)
    
    return render_template('rss.html', items=items, environ=os.environ, page_title=page_title)

def clean_xml_content(raw_content):
    # Escape illegal XML characters
    cleaned_content = re.sub(r'&(?!(amp|lt|gt|quot|#39|#x\d+);)', '&amp;', raw_content)
    return cleaned_content


############################################################################################################

@rss.route('/refresh/', methods=['POST'])
def trigger_rss_refresh():
    expected_token = os.getenv('RSS_REFRESH_TOKEN')
    token = request.headers.get('Authorization')
    
    if not token or token != expected_token:
        abort(403)
    
    print("RSS REFRESH STARTED")
    
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    # Grab all the RSS feed URLs from the database
    cursor.execute(rssdb.rss_feeds_select_all())
    feeds = cursor.fetchall()
    
    for feed in feeds:
        rss_feed_id, rss_feed_title, rss_feed_url = feed
        print(f"Processing feed {rss_feed_title} ({rss_feed_url})")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
           
            response = requests.get(rss_feed_url, headers=headers)
            response.raise_for_status()
            cleaned_content = clean_xml_content(response.text)
            root = ET.fromstring(cleaned_content)
            
            print("ROOT TAG: ", root.tag)
            
            # Check if this is an Atom feed
            if root.tag == '{http://www.w3.org/2005/Atom}feed':
                entry_tag = '{http://www.w3.org/2005/Atom}entry'
                title_tag = '{http://www.w3.org/2005/Atom}title'
                link_tag = '{http://www.w3.org/2005/Atom}link'
                description_tag = '{http://www.w3.org/2005/Atom}summary'
                date_tag = '{http://www.w3.org/2005/Atom}updated'
            else:
                # Assuming RSS if not Atom
                entry_tag = 'item'
                title_tag = 'title'
                link_tag = 'link'
                description_tag = 'description'
                date_tag = 'pubDate'
            
            for item in root.findall('.//' + entry_tag):                
                title = None
                link = None
                image_url = None
                description = None
                pub_date = None
                
                for elem in item:
                    # Attempt to find an image URL in <enclosure> or any <url> tag
                    if elem.tag == 'enclosure' and 'url' in elem.attrib:
                        image_url = elem.attrib['url']
                    elif elem.tag.endswith('url'):  # This is a simplification and might need adjustment based on actual feed structure
                        image_url = elem.text
                    
                    if elem.tag.endswith(title_tag):
                        title = elem.text
                    elif elem.tag.endswith(link_tag):
                        link = elem.attrib.get('href') if 'href' in elem.attrib else elem.text
                    elif elem.tag.endswith(description_tag):
                        description = bleach.clean(elem.text, tags=[], strip=True)
                    elif elem.tag.endswith(date_tag):
                        dt_obj = dup.parse(elem.text)
                        if dt_obj.tzinfo is None:
                            dt_obj = dt_obj.replace(tzinfo=dutz.tzutc())                         
                        pub_date = int(dt_obj.timestamp())
                
                print(f"Title: {title}")
                print(f"Link: {link}")
                print(f"Datetime: {pub_date}")
                
                # Put it in the databse. Before inserting, check if the item already exists to avoid duplicates
                cursor.execute(rssdb.rss_items_select_count_by_url(), (link,))
                count = cursor.fetchone()[0]
                print(f"Count found for URL {link}: {count}")
                
                if count == 0:
                    try:
                        cursor.execute(rssdb.rss_items_insert_new(), (rss_feed_id, link, title, image_url, description, pub_date, dt.datetime.now(), dt.datetime.now()))
                        new_connection.commit()
                        print(f"Inserted new item: {title}")
                    except Exception as e:
                        log.log_message(f"Failed to process feed {title}: {e}")
                        print(f"Error: {e}")
        except ET.ParseError as e:
            log.log_message(f"XML parsing failed for feed {rss_feed_url}: {e}")
        except requests.HTTPError as e:
            log.log_message(f"HTTP request failed for feed {rss_feed_url}: {e}")
        except requests.RequestException as e:
            log.log_message(f"HTTP request failed for feed {rss_feed_url}: {e}")
        except Exception as e:
            log.log_message(f"Failed to process feed {rss_feed_url}: {e}")
    
    new_connection.commit()
    cursor.close()
    db.db_connect_close(new_connection)
    
    return jsonify({'status': 'success', 'message': 'Process started.'}), 200


@rss.route('/generate_image/')
def rss_generate_image():
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    cursor.execute(rssdb.rss_items_select_random())
    item = cursor.fetchone()
    
    item = {
        'title': item[0],
        'date': item[5].strftime('%d/%m/%Y'),
        'feed': item[2],
        'description': item[4],
        'link': item[1]
    }
    
    cursor.close()
    db.db_connect_close(new_connection)
    
    return render_template('rss_generate_image.html', environ=os.environ, item=item)


@rss.route('/feeds/delete/', methods=['POST'])
def feeds_delete():
    print("INSIDE DELETE FEED")
    
    data = request.json
    feed_id = data['feed_id']

    new_connection = db.db_connect_open()   
    cursor = new_connection.cursor()

    cursor.execute(rssdb.rss_items_delete_by_feed_id(), (feed_id,))
    cursor.execute(rssdb.rss_feeds_delete_by_id(), (feed_id,))
    new_connection.commit()

    cursor.close()
    db.db_connect_close(new_connection)

    return jsonify({'success': 'Article type deleted successfully.'})


@sck.socketio.on('get_rss_image')
def get_rss_image(data):
    rss_image_prompt = data['prompt']
    print("PROMPT: ", rss_image_prompt)
    
    response = api.ai_openai.images.generate(
    model="dall-e-3",
    prompt=rss_image_prompt,
    size="1024x1024",
    quality="standard",
    n=1,
    )

    image_url = response.data[0].url
    print("IMAGE URL: ", image_url)

    sck.socketio.emit('image_generated', {'image_url': image_url})
    return