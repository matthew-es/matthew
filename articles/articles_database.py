from flask import current_app

import common.database as db
import common.logger as log

def get_table_names():
    prefix = current_app.config.get('TABLE_PREFIX', 'default')
    article_types_table = f"{prefix}_article_types"
    articles_table = f"{prefix}_articles"    
    return article_types_table, articles_table

def check_or_create_tables():
    article_types_table, articles_table = get_table_names()
    
    function_name = "ARTICLES: CHECK OR CREATE TABLES"
    log_check_or_create_articles_tables = log.log_duration_start(function_name)

    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()

    cursor.execute("""
                   SELECT EXISTS (
                        SELECT 1
                        FROM pg_catalog.pg_proc p
                        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname = 'public'  -- or your specific schema
                        AND p.proname = 'update_updatedat_column'  -- your function name
                    );
                    """)
    if not cursor.fetchone()[0]:
        cursor.execute(create_shared_functions())
        log.log_message("CREATED FUNCTIONS: updatedat")
    else:
        log.log_message("FUNCTION: updatedat already exists")
    
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{article_types_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(article_types_create_table())
        log.log_message(f"CREATED TABLE: {article_types_table}")
    else:
        log.log_message(f"TABLE: {article_types_table} already exists")    

    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{articles_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(articles_create_table())
        log.log_message(f"CREATED TABLE: {articles_table}")
    else:
        log.log_message(f"TABLE: {articles_table} already exists")

    new_connection.commit()
    cursor.close()
    db.db_connect_close(new_connection)    
    log.log_duration_end(log_check_or_create_articles_tables)
    
##########################################################################################################################
##########################################################################################################################

def create_shared_functions():
    return """
        CREATE OR REPLACE FUNCTION update_updatedat_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updatedat = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """

def article_types_create_table():
    article_types_table, articles_table = get_table_names()
    return f"""
        CREATE TABLE {article_types_table} (
        article_type_id SERIAL PRIMARY KEY,
        article_type_name VARCHAR(255) NOT NULL,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TRIGGER update_{article_types_table}_modtime
            BEFORE UPDATE ON {article_types_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """

def articles_create_table():
    article_types_table, articles_table = get_table_names()
    return f"""
        CREATE TABLE {articles_table} (
        article_id SERIAL PRIMARY KEY,
        article_type_id INTEGER NOT NULL,
        article_title TEXT NOT NULL,
        article_slug VARCHAR(255),
        article_lede TEXT,
        article_image TEXT,
        article_text TEXT,
        article_publish_date BIGINT,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_type_id) REFERENCES {article_types_table}(article_type_id)
    );
    
    CREATE TRIGGER update_{articles_table}_modtime
            BEFORE UPDATE ON {articles_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """

##########################################################################################################################
##########################################################################################################################

def article_types_select_all():
    article_types_table, articles_table = get_table_names()
    return f'''
            SELECT article_type_id, article_type_name
            FROM {article_types_table}
            ORDER BY article_type_name
        '''

def article_types_select_by_id():
    article_types_table, articles_table = get_table_names()
    return f'''
            SELECT article_type_name
            FROM {article_types_table}
            WHERE article_type_id = %s
        '''    

def article_types_insert_new():
    article_types_table, articles_table = get_table_names()
    return f'''
            INSERT INTO {article_types_table} (article_type_name)
            VALUES (%s)
        '''

def article_types_update_by_id():
    article_types_table, articles_table = get_table_names()
    return f"""
            UPDATE {article_types_table}
            SET article_type_name = %s
            WHERE article_type_id = %s
        """
        
def article_types_delete_by_id():
    article_types_table, articles_table = get_table_names()
    return f"DELETE FROM {article_types_table} WHERE article_type_id = %s"

def articles_count_by_article_type():
    article_types_table, articles_table = get_table_names()
    return f"""
        SELECT at.article_type_id, at.article_type_name, COUNT(a.article_id) AS article_count
        FROM {article_types_table} at
        LEFT JOIN {articles_table} a ON at.article_type_id = a.article_type_id
        GROUP BY at.article_type_id
        ORDER BY at.article_type_name ASC
    """

def articles_select_all():
    article_types_table, articles_table = get_table_names()
    return f'''
            SELECT a.article_id, a.article_title, a.article_slug, a.article_lede, a.article_image, a.article_text, a.article_publish_date, t.article_type_name
            FROM {articles_table} a
            LEFT JOIN {article_types_table} t ON a.article_type_id = t.article_type_id
            ORDER BY a.article_publish_date DESC
        '''

def articles_select_all_by_id():
    article_types_table, articles_table = get_table_names()
    return f'''
            SELECT article_id, article_title, article_lede, article_image, article_text, article_publish_date, article_type_id, article_slug
            FROM {articles_table}
            WHERE article_id = %s
        '''

def articles_select_all_by_slug():
    article_types_table, articles_table = get_table_names()
    return f'''
            SELECT article_id, article_title, article_lede, article_image, article_text, article_publish_date, article_type_id, article_slug
            FROM {articles_table}
            WHERE article_slug = %s
        '''

def articles_insert_new():
    print(f"DB: inside articles_insert_new")
    article_types_table, articles_table = get_table_names()
    print(f"DB: article_types_table: {articles_table}")
    return f'''
            INSERT INTO {articles_table} (article_type_id, article_title, article_slug, article_lede, article_image, article_text, article_publish_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''

def articles_select_article_image():
    article_types_table, articles_table = get_table_names()
    return f'''
            SELECT article_image
            FROM {articles_table}
            WHERE article_id = %s
        '''

def articles_update_article():
    article_types_table, articles_table = get_table_names()
    return f'''
            UPDATE {articles_table}
            SET article_type_id = %s, article_title = %s, article_slug = %s, article_lede = %s, article_image = %s, article_text = %s, article_publish_date = %s
            WHERE article_id = %s
        '''
        
def articles_delete_by_id():
    _, articles_table = get_table_names()
    return f"DELETE FROM {articles_table} WHERE article_id = %s"