import mysql.connector
from config import Config


def get_db_connection():
    """Create and return a MySQL database connection."""
    connection = mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    return connection
