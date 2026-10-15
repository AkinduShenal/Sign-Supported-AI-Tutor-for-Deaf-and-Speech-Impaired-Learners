try:
    import psycopg2 as psycopg_driver
except ImportError:
    try:
        import psycopg as psycopg_driver
    except ImportError:
        raise ImportError("Neither psycopg2 nor psycopg is installed. Please install psycopg or psycopg2-binary.")

import os
from datetime import datetime
from dotenv import load_dotenv

# Load env variables for DB connection from the ROOT folder's .env file
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT_ENV_PATH = os.path.join(ROOT_DIR, ".env")
if os.path.exists(ROOT_ENV_PATH):
    load_dotenv(ROOT_ENV_PATH)
else:
    load_dotenv()

def get_conn():
    db_url = os.getenv("DATABASE_URL")
    
    # Strip SQLAlchemy dialect prefixes so psycopg/psycopg2 can connect
    if db_url.startswith("postgresql+psycopg://"):
        db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
    elif db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
        
    return psycopg_driver.connect(db_url)

def init_db():
    try:
        conn = get_conn()
        c = conn.cursor()
        
        # Only ai_tutor_ml_insights table is used
        c.execute('''
            CREATE TABLE IF NOT EXISTS ai_tutor_ml_insights (
                user_id TEXT,
                category TEXT,
                past_attempts INTEGER,
                is_issue BOOLEAN,
                last_updated TEXT,
                PRIMARY KEY (user_id, category)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS ai_tutor_finishers (
                user_id TEXT PRIMARY KEY,
                completed_at TEXT
            )
        ''')
        conn.commit()  # Commit table creation first
        
        try:
            c.execute('ALTER TABLE ai_tutor_ml_insights RENAME COLUMN is_persistent TO is_issue')
            conn.commit()
            print("[INFO] Migrated column 'is_persistent' to 'is_issue'")
        except Exception:
            conn.rollback()
            
        conn.close()
        print("[SUCCESS] PostgreSQL ml_insights and finishers tables initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to PostgreSQL: {e}")

def get_user_ml_insights(user_id: str) -> dict:
    """Fetch all ML insights for a given user, keyed by category."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT category, past_attempts, is_issue, last_updated FROM ai_tutor_ml_insights WHERE user_id = %s', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    insights = {}
    for cat, attempts, is_iss, updated in rows:
        insights[cat] = {
            "past_attempts": attempts,
            "is_issue": is_iss,
            "last_updated": updated
        }
    return insights

def save_ml_insight(user_id: str, category: str, past_attempts: int, is_issue: bool):
    """Upsert the ML insight record for a user and category."""
    conn = get_conn()
    c = conn.cursor()
    ts = datetime.utcnow().isoformat()
    c.execute('''
        INSERT INTO ai_tutor_ml_insights (user_id, category, past_attempts, is_issue, last_updated) 
        VALUES (%s, %s, %s, %s, %s) 
        ON CONFLICT (user_id, category) DO UPDATE SET 
            past_attempts = EXCLUDED.past_attempts, 
            is_issue = EXCLUDED.is_issue, 
            last_updated = EXCLUDED.last_updated
    ''', (user_id, category, past_attempts, is_issue, ts))
    conn.commit()
    conn.close()

def resolve_all_user_ml_insights(user_id: str, categories: list):
    """Mark is_issue = False and update last_updated when user answers correctly."""
    if not categories:
        return
    conn = get_conn()
    c = conn.cursor()
    ts = datetime.utcnow().isoformat()
    for cat in categories:
        c.execute('''
            INSERT INTO ai_tutor_ml_insights (user_id, category, past_attempts, is_issue, last_updated)
            VALUES (%s, %s, 1, FALSE, %s)
            ON CONFLICT (user_id, category) DO UPDATE SET
                is_issue = FALSE,
                last_updated = EXCLUDED.last_updated
        ''', (user_id, cat, ts))
    conn.commit()
    conn.close()

def has_user_finished(user_id: str) -> bool:
    """Check if the user is in the ai_tutor_finishers table."""
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT 1 FROM ai_tutor_finishers WHERE user_id = %s', (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row)

def mark_user_finished(user_id: str):
    """Insert user into ai_tutor_finishers table."""
    conn = get_conn()
    c = conn.cursor()
    ts = datetime.utcnow().isoformat()
    c.execute('''
        INSERT INTO ai_tutor_finishers (user_id, completed_at)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO NOTHING
    ''', (user_id, ts))
    conn.commit()
    conn.close()
