from flask import current_app

import common.database as db
import common.logger as log

def get_table_names():    
    prefix = current_app.config.get('TABLE_PREFIX', 'default')
    rss_feeds_table = f"{prefix}_rss_feeds"
    rss_items_table = f"{prefix}_rss_items"
    
    
    return rss_feeds_table, rss_items_table

def check_or_create_tables():
    rss_feeds_table, rss_items_table = get_table_names()
    
    function_name = "RSS: CHECK OR CREATE TABLES"
    log_check_or_create_rss_tables = log.log_duration_start(function_name)

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
    
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{rss_feeds_table}');")
    if not cursor.fetchone()[0]:
        cursor.execute(rss_feeds_create_table())
        log.log_message(f"CREATED TABLE: {rss_feeds_table}")
    else:
        log.log_message(f"TABLE: {rss_feeds_table} already exists")
     
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{rss_items_table}');")
    if not cursor.fetchone()[0]:
        cursor.execute(rss_items_create_table())
        log.log_message(f"CREATED TABLE: {rss_items_table}")
        feeds = [
            ("WSJ Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
            ("FT Commodities", "https://www.ft.com/commodities?format=rss"),
            ("BBC Business", "http://feeds.bbci.co.uk/news/business/rss.xml"),
            ("UN Asia", "https://news.un.org/feed/subscribe/en/news/region/asia-pacific/feed/rss.xml"),
            ("Guardian Business", "https://www.theguardian.com/uk/business/rss")
        ]

        cursor.executemany(f"""
            INSERT INTO {rss_feeds_table} (rss_feed_title, rss_feed_url)
            VALUES (%s, %s)
            ON CONFLICT (rss_feed_url) DO NOTHING;
        """, feeds)
    else:
        log.log_message(f"TABLE: {rss_items_table} already exists")

    new_connection.commit()
    cursor.close()
    db.db_connect_close(new_connection)    
    log.log_duration_end(log_check_or_create_rss_tables)
    
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
    
def rss_feeds_create_table():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"""
        CREATE TABLE {rss_feeds_table} (
        rss_feed_id SERIAL PRIMARY KEY,
        rss_feed_title TEXT NOT NULL,
        rss_feed_url TEXT NOT NULL UNIQUE,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TRIGGER update_{rss_feeds_table}_modtime
            BEFORE UPDATE ON {rss_feeds_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """

def rss_items_create_table():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"""
        CREATE TABLE {rss_items_table} (
        rss_item_id SERIAL PRIMARY KEY,
        rss_feed_id INTEGER NOT NULL,
        rss_item_url TEXT,
        rss_item_title TEXT,
        rss_item_image TEXT,
        rss_item_description TEXT,
        rss_item_date TIMESTAMP WITH TIME ZONE,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rss_feed_id) REFERENCES {rss_feeds_table}(rss_feed_id)
    );
    
    CREATE TRIGGER update_{rss_items_table}_modtime
            BEFORE UPDATE ON {rss_items_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """
    
##########################################################################################################################
##########################################################################################################################

def rss_feeds_select_all():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"SELECT rss_feed_id, rss_feed_title, rss_feed_url FROM {rss_feeds_table}"

def rss_feeds_insert_new():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"INSERT INTO {rss_feeds_table} (rss_feed_title, rss_feed_url) VALUES (%s, %s) ON CONFLICT (rss_feed_url) DO NOTHING"

def rss_feeds_delete_by_id():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"DELETE FROM {rss_feeds_table} WHERE rss_feed_id = %s"

def rss_items_select_all():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"""
        SELECT r.rss_item_title, r.rss_item_url, f.rss_feed_title, r.rss_item_image, r.rss_item_description, r.rss_item_date 
        FROM {rss_items_table} r
        JOIN {rss_feeds_table} f ON r.rss_feed_id = f.rss_feed_id
        ORDER BY r.rss_item_date desc;
        """

def rss_items_select_random():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"""
        SELECT r.rss_item_title, r.rss_item_url, f.rss_feed_title, r.rss_item_image, r.rss_item_description, r.createdat 
        FROM {rss_items_table} r
        JOIN {rss_feeds_table} f ON r.rss_feed_id = f.rss_feed_id
        WHERE rss_item_image IS NULL ORDER BY RANDOM() LIMIT 1;
        """

def rss_items_select_count_by_url():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"SELECT COUNT(*) FROM {rss_items_table} WHERE rss_item_url = %s"

def rss_items_insert_new():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"INSERT INTO {rss_items_table} (rss_feed_id, rss_item_url, rss_item_title, rss_item_image, rss_item_description, rss_item_date, createdat, updatedat) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"

def rss_items_delete_by_feed_id():
    rss_feeds_table, rss_items_table = get_table_names()
    return f"DELETE FROM {rss_items_table} WHERE rss_feed_id = %s"