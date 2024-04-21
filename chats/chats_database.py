from flask import current_app

import common.database as db
import common.logger as log

def get_table_names():    
    prefix = current_app.config.get('TABLE_PREFIX', 'default')
    chats_prompts_table = f"{prefix}_chat_prompts"
    chats_chats_table = f"{prefix}_chats"
    chats_messages_table = f"{prefix}_chat_messages"
    users_table = f"{prefix}_users"
    llms_table = f"{prefix}_llms"
    return chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table

def check_or_create_tables():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    
    function_name = "CHATS: CHECK OR CREATE TABLES"
    log_check_or_create_chats_tables = log.log_duration_start(function_name)

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
    
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{chats_prompts_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(chats_prompts_create_table())
        log.log_message(f"CREATED TABLE: {chats_prompts_table}")
    else:
        log.log_message(f"TABLE: {chats_prompts_table} already exists")
        
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{chats_chats_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(chats_chats_create_table())
        log.log_message(f"CREATED TABLE: {chats_chats_table}")
    else:
        log.log_message(f"TABLE: {chats_chats_table} already exists")
        
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{chats_messages_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(chats_messages_create_table())
        log.log_message(f"CREATED TABLE: {chats_messages_table}")
    else:
        log.log_message(f"TABLE: {chats_messages_table} already exists")

    new_connection.commit()
    cursor.close()
    db.db_connect_close(new_connection)    
    log.log_duration_end(log_check_or_create_chats_tables)
    
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
    

def chats_prompts_create_table():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"""
        CREATE TABLE {chats_prompts_table} (
        chat_prompt_id SERIAL PRIMARY KEY,
        chat_prompt_title VARCHAR(255) NOT NULL,
        chat_prompt_text TEXT,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TRIGGER update_{chats_prompts_table}_modtime
            BEFORE UPDATE ON {chats_prompts_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """

def chats_chats_create_table():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"""
        CREATE TABLE {chats_chats_table} (
        chat_id SERIAL PRIMARY KEY,
        user_id UUID NOT NULL,
        llm_id INTEGER NOT NULL,
        chat_prompt_id INTEGER NOT NULL,
        chat_model VARCHAR(255) NOT NULL,
        chat_prompt_title VARCHAR(255),
        chat_prompt_text TEXT,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES {users_table}(uuid),
        FOREIGN KEY (llm_id) REFERENCES {llms_table}(llm_id),
        FOREIGN KEY (chat_prompt_id) REFERENCES {chats_prompts_table}(chat_prompt_id)
    );
    
    CREATE TRIGGER update_{chats_chats_table}_modtime
            BEFORE UPDATE ON {chats_chats_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """

def chats_messages_create_table():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"""
        CREATE TABLE {chats_messages_table} (
        chat_message_id SERIAL PRIMARY KEY,
        chat_id INTEGER NOT NULL,
        user_id UUID NOT NULL,
        chat_message_content TEXT,
        chat_message_type VARCHAR(255) NOT NULL,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES {chats_chats_table}(chat_id),
        FOREIGN KEY (user_id) REFERENCES {users_table}(uuid)
    );
    
    CREATE TRIGGER update_{chats_messages_table}_modtime
            BEFORE UPDATE ON {chats_messages_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """
    
##########################################################################################################################
##########################################################################################################################

def chats_select_all_by_id():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT chat_id FROM {chats_chats_table} ORDER BY chat_id"

def chats_prompts_select_all_all():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT chat_prompt_id, chat_prompt_title, chat_prompt_text FROM {chats_prompts_table} ORDER BY chat_prompt_id"

def chats_prompts_select_all_id_title():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT chat_prompt_id, chat_prompt_title FROM {chats_prompts_table} ORDER BY chat_prompt_title DESC"

def chats_prompts_insert_new():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"INSERT INTO {chats_prompts_table} (chat_prompt_title, chat_prompt_text) VALUES (%s, %s) RETURNING chat_prompt_id"

def chats_prompts_update():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"UPDATE {chats_prompts_table} SET chat_prompt_title = %s, chat_prompt_text = %s WHERE chat_prompt_id = %s"

def chats_prompts_select_by_id():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT chat_prompt_id, chat_prompt_title, chat_prompt_text FROM {chats_prompts_table} WHERE chat_prompt_id = %s"

def chats_prompts_select_one_title_text():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT chat_prompt_title, chat_prompt_text FROM {chats_prompts_table} WHERE chat_prompt_id = %s"

def chats_llms_select_all_id_title():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT llm_id, llm_title FROM {llms_table} ORDER BY llm_title DESC"

def chats_llms_select_title_by_id():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT llm_title FROM {llms_table} WHERE llm_id = %s"

def chats_insert_new():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"INSERT INTO {chats_chats_table} (user_id, llm_id, llm_title, chat_prompt_id, chat_prompt_title, chat_prompt_text) VALUES (%s, %s, %s, %s, %s, %s) RETURNING chat_id;"

def chats_messages_insert_question():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"INSERT INTO {chats_messages_table} (chat_id, user_id, chat_message_content, chat_message_type) VALUES (%s, %s, %s, 'question')"

def chats_messages_insert_answer():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"INSERT INTO {chats_messages_table} (chat_id, user_id, chat_message_content, chat_message_type) VALUES (%s, %s, %s, 'answer')"

def chats_messages_select_all_by_chat_id():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT chat_message_content, chat_message_type FROM {chats_messages_table} WHERE chat_id = %s ORDER BY chat_message_id"

def chats_select_details_by_chat_id():
    chats_prompts_table, chats_chats_table, chats_messages_table, users_table, llms_table = get_table_names()
    return f"SELECT llm_title, chat_prompt_id, chat_prompt_title, chat_prompt_text FROM {chats_chats_table} WHERE chat_id = %s"