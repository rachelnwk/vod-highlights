import pymysql
from pymysql.cursors import DictCursor

from config.reader import CONFIG, require_value

DB_HOST = require_value("rds", "endpoint")
DB_PORT = CONFIG.getint("rds", "port_number")
DB_USER = require_value("rds", "user_name")
DB_PASSWORD = require_value("rds", "user_pwd")
DB_NAME = require_value("rds", "db_name")


# Purpose: Open a new PyMySQL connection using the configured RDS settings.
# Input: No arguments.
# Output: Active PyMySQL connection object.
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,
        autocommit=False,
    )
