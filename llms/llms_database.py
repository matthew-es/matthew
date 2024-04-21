from flask import current_app

import common.database as db
import common.logger as log

def get_table_names():
    prefix = current_app.config.get('TABLE_PREFIX', 'default')
    llms_table = f"{prefix}_llms"
    
    return llms_table

def check_or_create_tables():
    llms_table = get_table_names()
    
    function_name = "LLMS: CHECK OR CREATE TABLES"
    log_check_or_create_users_tables = log.log_duration_start(function_name)
    
    new_connection = db.db_connect_open()
    cursor = new_connection.cursor()
  
    cursor.execute("""
                   SELECT EXISTS (
                        SELECT 1
                        FROM pg_catalog.pg_proc p
                        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname = 'public'
                        AND p.proname = 'update_updatedat_column'
                    );
                    """)
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(create_shared_functions())
        log.log_message("CREATED FUNCTIONS: updatedat")
    else:
        log.log_message("FUNCTION: updatedat already exists")
    
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{llms_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(llms_create_table())
        log.log_message(f"CREATED TABLE: {llms_table}")
    else:
        log.log_message(f"TABLE: {llms_table} already exists")
    
    models = [
        (1, "gpt-4-turbo-2024-04-09"),
        (2, "gpt-4-0125-preview"),
        (3, "gpt-3.5-turbo-0125"),
        (4, "claude-3-opus-20240229"),
        (5, "claude-3-sonnet-20240229"),
        (6, "claude-3-haiku-20240307")
    ]
    cursor.executemany(f"""
        INSERT INTO {llms_table} (llm_id, llm_title)
        VALUES (%s, %s)
        ON CONFLICT (llm_id) DO NOTHING;
    """, models)
    
    
    new_connection.commit()
    cursor.close()
    db.db_connect_close(new_connection)    
    log.log_duration_end(log_check_or_create_users_tables)
    
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
    
def llms_create_table():
    llms_table = get_table_names()
    return f"""
        CREATE TABLE {llms_table} (
        llm_id SERIAL PRIMARY KEY,
        llm_title VARCHAR(255) NOT NULL,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TRIGGER update_{llms_table}_modtime
            BEFORE UPDATE ON {llms_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """