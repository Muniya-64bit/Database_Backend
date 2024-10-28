import logging
import os
from mysql.connector import pooling, connect, Error
from dotenv import load_dotenv

load_dotenv()

# Define global connection pools for admin, supervisor, and employee
admin_pool = pooling.MySQLConnectionPool(
    pool_name="admin_pool",
    pool_size=5,
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_ADMIN_USER'),
    password=os.getenv('DB_ADMIN_PASSWORD'),
    database=os.getenv('DB_NAME')
)

supervisor_pool = pooling.MySQLConnectionPool(
    pool_name="supervisor_pool",
    pool_size=50,
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_SUPERVISOR_USER'),
    password=os.getenv('DB_SUPERVISOR_PASSWORD'),
    database=os.getenv('DB_NAME')
)

employee_pool = pooling.MySQLConnectionPool(
    pool_name="employee_pool",
    pool_size=1000,
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_EMPLOYEE_USER'),
    password=os.getenv('DB_EMPLOYEE_PASSWORD'),
    database=os.getenv('DB_NAME')
)

# Retrieve a connection based on role
async def get_db(role='employee'):
    try:
        if role == 'admin':
            conn = admin_pool.get_connection()
        elif role == 'supervisor':
            conn = supervisor_pool.get_connection()
        else:
            conn = employee_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        yield cursor, conn
    finally:
        cursor.close()
        conn.close()

