import sqlite3

def connect():
    # Changed database name to force a fresh start
    return sqlite3.connect("truthlens_data.db", check_same_thread=False, timeout=10)

def create_tables():
    conn = connect()
    c = conn.cursor()
    # 1. History Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        email TEXT,
        news TEXT,
        result TEXT,
        confidence REAL
    )
    """)
    # 2. Users Table (Registration-ku ithu thaan mukkiyam)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

# App start aagum pothu intha function-a call pannanum
create_tables()

def save_history(email, news, result, confidence):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO history (email, news, result, confidence) VALUES (?, ?, ?, ?)",
              (email, news, result, confidence))
    conn.commit()
    conn.close()

def get_user_history(email):
    conn = connect()
    c = conn.cursor()
    # 'id' ku bathila built-in 'rowid' use pandrom. Ithu fail aagave aagathu!
    c.execute("SELECT email, news, result, confidence FROM history WHERE email=? ORDER BY rowid DESC", (email,))
    data = c.fetchall()
    conn.close()
    return data


    