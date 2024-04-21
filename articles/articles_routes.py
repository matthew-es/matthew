from . import articles
from flask import render_template, redirect, url_for, request, flash, jsonify

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
import articles.articles_database as artdb

############################################################################################################

@articles.route('/')
def index(): 
    page_title = "Articles Index"

    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
        
    cursor.execute(artdb.articles_select_all())
    articles_list = cursor.fetchall()
    
    for article in articles_list:
        print(article)
    
    articles = [{
            'id': article[0],
            'type': article[7],
            'title': article[1],
            'slug': article[2],
            'lede': article[3],
            'image': article[4],
            'text': article[5],
            'publishdate': article[6],
            'formatted_publishdate': dt.datetime.utcfromtimestamp(article[6]).strftime('%d/%m/%Y')
        }
        for article in articles_list
                ]

    print(articles)

    cursor.close()
    db.db_connect_close(new_connection)

    return render_template('articles_list.html', articles=articles, environ=os.environ, page_title=page_title)

# @articles.route('/<string:article_slug>/')
# def articles_show_slug(article_slug):
#     print(f"Article Slug: {article_slug}")
#     return f"Article Slug: {article_slug}", 200

@articles.route('/<string:article_slug>/')
@articles.route('/<int:article_id>/')
@articles.route('/<int:article_id>/<string:article_slug>/')
def articles_show(article_id=None, article_slug=None):
    try:
        print(f"Article ID ON START: {article_id}")
        print(f"Article Slug ON START: {article_slug}")
        
        new_connection = db.db_connect_open()
        cursor = new_connection.cursor()
        
        if article_id:
            cursor.execute(artdb.articles_select_all_by_id(), (article_id,))
        elif article_slug and not article_id:
            cursor.execute(artdb.articles_select_all_by_slug(), (article_slug,))

        article = cursor.fetchone()
        
        print(f"Article: {article}")
        
        if not article:
            cursor.close()
            db.db_connect_close(new_connection)
            return "Article not found", 404
        
        article_id = article[0]
        article_slug = article[7]
        
        print(article)
        print(f"Article ID AFTER LOGIC: {article_id}")
        print(f"Article Slug AFTER LOGIC: {article_slug}")
            
        cursor.execute(artdb.article_types_select_by_id(), (article[6],))
        article_type_name = cursor.fetchone()[0]
        
        cursor.close()
        db.db_connect_close(new_connection)
        
        if not request.path.endswith(f"/{article_id}/{article_slug}/"):
            new_url = f'/articles/{article_id}/{article_slug}/'
            return redirect(new_url, code=301)
        
        print(f"Publish Date Raw Value: {article[5]}, Type: {type(article[5])}")
        
        article = {
            'id': article[0],
            'type': article_type_name,
            'title': article[1],
            'lede': article[2],
            'image': article[3],
            'text': markdown.markdown(article[4]),
            'publishdate': article[5],
            'formatted_publishdate': dt.datetime.utcfromtimestamp(article[5]).strftime('%d/%m/%Y')
        }
        
        page_title = article['title']
        
        return render_template('articles_display.html', article=article, environ=os.environ, page_title=page_title)
    except Exception as e:
        print(f"Error: {e}")
        return "Article not found", 404
    
############################################################################################################

@articles.route('/types/', methods=['GET', 'POST'])
def article_types():
    page_title = "Article Types"

    new_connection = db.db_connect_open()   
    cursor = new_connection.cursor()

    if request.method == 'POST':
        new_type_name = request.form.get('type_name')
        if new_type_name:
            cursor.execute(artdb.article_types_insert_new(), (new_type_name,))
            new_connection.commit()
        
        return redirect(url_for('articles.article_types'))

    cursor.execute(artdb.article_types_select_all())
    article_types = cursor.fetchall()
    
    cursor.execute(artdb.articles_count_by_article_type())
    article_types = cursor.fetchall()
    article_types_list = [{
        'id': at[0], 
        'name': at[1], 
        'count': at[2]
        } for at in article_types]

    cursor.close()
    db.db_connect_close(new_connection)

    return render_template('articles_types.html', article_types=article_types_list, environ=os.environ, page_title=page_title)

@articles.route('/update-article-type/', methods=['POST'])
def update_article_type():
    data = request.json
    article_type_id = data['article_type_id']
    new_name = data['new_name']

    new_connection = db.db_connect_open()   
    cursor = new_connection.cursor()

    # Update the article type
    cursor.execute(artdb.article_types_update_by_id(), (new_name, article_type_id))
    new_connection.commit()

    cursor.close()
    db.db_connect_close(new_connection)

    return jsonify({'success': 'Article type updated successfully.'})

@articles.route('/delete-article-type/', methods=['POST'])
def delete_article_type():
    data = request.json
    article_type_id = data['article_type_id']

    new_connection = db.db_connect_open()   
    cursor = new_connection.cursor()

    cursor.execute(artdb.article_types_delete_by_id(), (article_type_id,))
    new_connection.commit()

    cursor.close()
    db.db_connect_close(new_connection)

    return jsonify({'success': 'Article type deleted successfully.'})

############################################################################################################

@articles.route('/new/', methods=['GET', 'POST'])
def create_article():
    page_title = "New Article"
    
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
    
    if request.method == 'POST':
        print("LET's do a new article!")
        
        article_type_id = request.form['article_type_id']
        title = request.form['title']
        slug = request.form['slug']
        lede = request.form['lede']
        image = request.files['image']
        text = request.form['text']
        publishdate = request.form['publishdate']
         
        publishdate_dt = dt.datetime.strptime(publishdate, '%d/%m/%Y')
        publishdate_dt = publishdate_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        publishdate_unix = int(publishdate_dt.replace(tzinfo=dt.timezone.utc).timestamp())

        image_url = None
        if image:
            blob_client = az.container_client.get_blob_client(blob=image.filename)
            blob_client.upload_blob(image, overwrite=True)
            image_url = blob_client.url

        print(f"Image URL: {image_url}")
        
        cursor.execute(artdb.articles_insert_new(), (article_type_id, title, slug, lede, image_url, text, publishdate_unix))
        new_connection.commit()
        return redirect('/articles')
    else:
        cursor.execute(artdb.article_types_select_all())
        new_connection.commit()
        article_types = cursor.fetchall()
    
    cursor.close()
    db.db_connect_close(new_connection)
    
    return render_template('articles_form.html', environ=os.environ, page_title=page_title, article_types=article_types)


@articles.route('/<int:article_id>/edit/', methods=['GET', 'POST'])
def edit_article(article_id):
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()

    if request.method == 'POST':
        article_type_id = request.form['article_type_id']
        title = request.form['title']
        slug = request.form['slug']
        lede = request.form['lede']
        image = request.files['image']
        publishdate = request.form['publishdate']
        text = request.form['text']
        
        publishdate_dt = dt.datetime.strptime(publishdate, '%d/%m/%Y')
        publishdate_dt = publishdate_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        publishdate_unix = int(publishdate_dt.replace(tzinfo=dt.timezone.utc).timestamp())
        
        image_url = None
        if image and image.filename:
            blob_client = az.container_client.get_blob_client(blob=image.filename)
            blob_client.upload_blob(image, overwrite=True)
            image_url = blob_client.url
        else:
            cursor.execute(artdb.articles_select_article_image(), (article_id,))
            article = cursor.fetchone()[0]
            image_url = article

        cursor.execute(artdb.articles_update_article(), (article_type_id, title, slug, lede, image_url, text, publishdate_unix, article_id))

        new_connection.commit()
        cursor.close()
        db.db_connect_close(new_connection)

        return redirect(url_for('articles.edit_article', article_id=article_id))
    else:
        cursor.execute(artdb.articles_select_all_by_id(), (article_id,))
        article = cursor.fetchone()
        
        cursor.execute(artdb.article_types_select_all())
        article_types = cursor.fetchall()
        
        cursor.close()
        db.db_connect_close(new_connection)
                
        print(article)
        article = {
            'id': article[0],
            'type': article[6],
            'title': article[1],
            'slug': article[7],
            'lede': article[2],
            'image': article[3],
            'text': article[4],
            'publishdate': article[5],
            'formatted_publishdate': dt.datetime.utcfromtimestamp(article[5]).strftime('%d/%m/%Y')
        }
        
        print(article)
        
        return render_template('articles_form.html', article=article, environ = os.environ, article_types=article_types)



@articles.route('/<int:article_id>/delete/', methods=['POST'])
def delete_article(article_id):
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()

    try:
        cursor.execute(artdb.articles_delete_by_id(), (article_id,))
        new_connection.commit()
        flash('Article deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting article: {e}', 'error')
        log.log_message(f"Error deleting article {article_id}: {e}")
    finally:
        cursor.close()
        db.db_connect_close(new_connection)

    return redirect(url_for('articles.index'))