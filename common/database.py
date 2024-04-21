import psycopg as pg
import os

import common.logger as log
import common.database as db

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
            #,
            #sslmode="require"
        )
        return connection
        
    except Exception as e:
        print("Unable to connect to the database from db_connect:", e)

# Close the connection to the database
def db_connect_close(connection):
    connection.close()
    log.log_message("DB CONNECTION CLOSED")


##########################################################################################
###### DO the tables exist? Do we need to create them?

def check_or_create_tables():
    function_name = "CHECK OR CREATE MAIN TABLES"
    log_check_or_create_tables = log.log_duration_start(function_name)
    
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
        new_connection.commit()
        log.log_message("CREATED FUNCTIONS: updatedat")
    else:
        log.log_message("FUNCTION: updatedat already exists")
    
    cursor.close() 
    db.db_connect_close(new_connection)
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