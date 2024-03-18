import psycopg as pg
import os
import matthew_logger as log

# Connect to postgres database with psycopg
def db_connect_open():        
    log.log_message("DB CONNECTION OPENED")
    
    try:
        connection = pg.connect(
            host = os.getenv("DATABASE_HOST"),
            dbname = os.getenv("DATABASE_NAME"),
            user = os.getenv("DATABASE_USER"),
            password = os.getenv("DATABASE_PASSWORD"),
            port = os.getenv("DATABASE_PORT")
            # ,
            # sslmode="require"
        )
        return connection
        
    except pg.OperationalError as e:
        print("Unable to connect to the database from db_connect:", e)

# Close the connection to the database
def db_connect_close(connection):
    connection.close()
    log.log_message("DB CONNECTION CLOSED")

##############################
###### DO the tables exist? Do we need to create them?
def check_or_create_tables(new_connection):
    function_name = "CHECK OR CREATE TABLES"
    log_check_or_create_tables = log.log_duration_start(function_name)
    
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
        new_connection.commit()
        log.log_message("CREATED FUNCTIONS: updatedat")
    else:
        log.log_message("FUNCTION: updatedat already exists")
    new_connection.commit()
    
    
    cursor = new_connection.cursor()
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'symbols');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(symbols_create_table())
        new_connection.commit()
        log.log_message("CREATED TABLE: symbols")
    else:
        log.log_message("TABLE: symbols already exists")
    new_connection.commit()

    
    cursor = new_connection.cursor()
    cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(users_create_table())
        new_connection.commit()
        log.log_message("CREATED TABLE: users")
    else:
        log.log_message("TABLE: users already exists")
    new_connection.commit()
    
    log.log_duration_end(log_check_or_create_tables)
    
##############################
###### CREATE TABLES statements

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

def matthew_users_create_table():
    return """        
        CREATE TABLE matthew_users (
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
        
        CREATE TRIGGER update_matthew_users_modtime
            BEFORE UPDATE ON matthew_users
            FOR EACH ROW
            EXECUTE FUNCTION update_updatedat_column();
    """

def matthew_chats_create_table():
    return """
        CREATE TABLE matthew_chats (
        chatid SERIAL PRIMARY KEY,
        userid UUID NOT NULL,
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (userid) REFERENCES matthew_users(uuid)
    );
    """

def matthew_messages_create_table():
    return """
        CREATE TABLE matthew_messages (
        messageid SERIAL PRIMARY KEY,
        chatid INTEGER NOT NULL,
        userid UUID NOT NULL,
        messagecontent TEXT,
        status VARCHAR(255),
        createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updatedat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chatid) REFERENCES matthew_chats(chatid),
        FOREIGN KEY (userid) REFERENCES matthew_users(uuid)
    );
    """

##############################
### OPERATIONS QUERIES ##################
# Symbols
def symbols_select_count():
    return "SELECT COUNT(*) FROM Symbols;"

def symbols_select_count_group_by_status():
    return "SELECT Status, COUNT(*) FROM Symbols GROUP BY Status;"

def symbols_select_symbol_on_name():
    return "SELECT SymbolID FROM Symbols WHERE SymbolName = %s;"

def symbols_select_status_trading_disabled():
    return "SELECT SymbolID, Status, TradingDisabled FROM Symbols WHERE SymbolName = %s;"

def symbols_select_status_online():
    return "SELECT SymbolName FROM Symbols WHERE Status = 'online';"

def symbols_update_status_trading_disabled():
    return "UPDATE Symbols SET Status = %s, TradingDisabled = %s WHERE SymbolID = %s;"

def symbols_insert_symbol():
    return "INSERT INTO Symbols (SymbolName, Status, TradingDisabled) VALUES (%s, %s, %s) RETURNING SymbolID;"