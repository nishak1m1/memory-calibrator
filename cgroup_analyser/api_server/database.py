import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()  # Optional: for local .env use

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", 5432)
    )

def get_max_usage(hostname: str, cgroup: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT max_usage FROM memory_usage
                WHERE hostname = %s AND cgroup = %s
                ORDER BY max_usage DESC LIMIT 1
            """, (hostname, cgroup))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        conn.close()

def insert_memory_usage(hostname: str, cgroup: str, max_usage: int, timestamp):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO memory_usage (hostname, cgroup, max_usage, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (hostname, cgroup, max_usage, timestamp))
            conn.commit()
    finally:
        conn.close()

def insert_constant_max_memory_usage(hostname: str, cgroup: str, max_usage: int, timestamp):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO constant_memory_usage (hostname, cgroup, max_usage, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (hostname, cgroup, max_usage, timestamp))
            conn.commit()
    finally:
        conn.close()
