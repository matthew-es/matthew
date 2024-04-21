from flask import current_app

import common.database as db
import common.logger as log

def get_table_names():    
    prefix = current_app.config.get('TABLE_PREFIX', 'default')
    users_table = f"{prefix}_users"
    
    return users_table

def check_or_create_tables():
    users_table = get_table_names()
    
    function_name = "USERS: CHECK OR CREATE TABLES"
    log_check_or_create_users_tables = log.log_duration_start(function_name)
    
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
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(create_shared_functions())
        log.log_message("CREATED FUNCTIONS: updatedat")
    else:
        log.log_message("FUNCTION: updatedat already exists")
    
    cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{users_table}');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(users_create_table())
        log.log_message(f"CREATED TABLE: {users_table}")
    else:
        log.log_message(f"TABLE: {users_table} already exists")
    
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

def users_create_table():
    users_table = get_table_names()
    
    return f"""        
        CREATE TABLE {users_table} (
            uuid uuid PRIMARY KEY,
            email varchar(255) UNIQUE NOT NULL,
            email_confirmed boolean NOT NULL DEFAULT false,
            email_confirm_token text,
            password_digest text NOT NULL,
            password_reset_token text,
            password_reset_expiry bigint,
            login_is_allowed boolean NOT NULL DEFAULT true,
            login_last_time bigint,
            login_failed_attempts integer NOT NULL DEFAULT 0,
            login_lockout_until bigint,
            can_access_level integer NOT NULL DEFAULT 0,
            can_access_until bigint,
            createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TRIGGER update_{users_table}_modtime
            BEFORE UPDATE ON {users_table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """