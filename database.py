from sqlalchemy import create_engine, text
from datetime import datetime
from rapidfuzz import fuzz
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Compose DB URL from .env variables for PostgreSQL

db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_name = os.environ.get('DB_NAME')
if db_user and db_password and db_host and db_name:
    DB_URL = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:5432/{db_name}"
else:
    raise RuntimeError("Database credentials are not set in .env. Please set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME.")
engine = create_engine(DB_URL)

def validate(username, password):
    # Added error handling for DB access and bcrypt
    try:
        query = text("SELECT first_name, last_name, password FROM users WHERE username = :username")
        with engine.connect() as conn:
            result = conn.execute(query, {"username": username}).fetchone()
            if result:
                stored_hash = result[2]
                if stored_hash.startswith("$2a$") or stored_hash.startswith("$2b$"):
                    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                        return {'first_name': result[0], 'last_name': result[1]}
                    else:
                        return None
                else:
                    print("[SECURITY] User has non-bcrypt password hash. Password reset required.")
                    return None
            return None
    except Exception as e:
        print(f"[ERROR] validate: {e}")
        return None

def register_user(first_name, last_name, username, password, branch):
    # Added error handling for DB access and hashing
    try:
        already_exist = text("SELECT * FROM users WHERE username = :username")
        with engine.connect() as conn:
            user = conn.execute(already_exist, {"username": username}).fetchone()
            if user:
                return False
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        query = text("""
             INSERT INTO users (first_name, last_name, username, password, branch)
             VALUES (:first_name, :last_name, :username, :password, :branch)
         """)
        with engine.connect() as conn:
            result = conn.execute(query, {
                "first_name": first_name,
                "last_name": last_name,
                "branch": branch,
                "username": username,
                "password": hashed
            })
            conn.commit()
            return True
    except Exception as e:
        print(f"[ERROR] register_user: {e}")
        return False

def file_data(uploaded_by, sub_name, branch, sem, year, desc, unit, filename, file_path):
    # Added error handling for DB insert
    try:
        query = text("""
            INSERT INTO uploaded_files (
                uploaded_by, sub_name, branch, sem, year, description, unit, filename, file_path, uploaded_at
            ) VALUES (
                :uploaded_by, :sub_name, :branch, :sem, :year, :description, :unit, :filename, :file_path, :uploaded_at
            )
        """)
        params = {
            'uploaded_by': uploaded_by,
            'sub_name': sub_name,
            'branch': branch,
            'sem': sem,
            'year': year,
            'description': desc,
            'unit': unit,
            'filename': filename,
            'file_path': file_path,
            'uploaded_at': datetime.now()
        }
        with engine.connect() as conn:
            result = conn.execute(query, params)
            conn.commit()
            if result:
                return True
            else:
                return False
    except Exception as e:
        print(f"[ERROR] file_data: {e}")
        return False

def get_dashbard_details(user_name):
    # Added error handling for DB fetch
    try:
        query = text("SELECT * FROM uploaded_files WHERE uploaded_by = :username")
        with engine.connect() as conn:
            result = conn.execute(query,{"username":user_name}).mappings().all()
        return result if result else False
    except Exception as e:
        print(f"[ERROR] get_dashbard_details: {e}")
        return False

def delete(id):
    # Added error handling for DB delete
    try:
        query = text("DELETE FROM uploaded_files WHERE id = :id")
        with engine.connect() as conn:
            result = conn.execute(query,{"id":id})
            conn.commit()
        print("file deleted")
        return True if result else False
    except Exception as e:
        print(f"[ERROR] delete: {e}")
        return False

def search_notes(search_query):
    # Added error handling for DB search
    try:
        like_query = f"%{search_query}%"
        query = text("""
            SELECT * FROM uploaded_files
            WHERE sub_name LIKE :q
               OR description LIKE :q
               OR unit LIKE :q
               OR filename LIKE :q
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"q": like_query}).mappings().all()
        if result:
            result = sorted(result, key=lambda row: max(
                fuzz.partial_ratio(search_query.lower(), str(row['sub_name']).lower()),
                fuzz.partial_ratio(search_query.lower(), str(row['description']).lower()),
                fuzz.partial_ratio(search_query.lower(), str(row['unit']).lower()),
                fuzz.partial_ratio(search_query.lower(), str(row['filename']).lower())
            ), reverse=True)
            return result
        return False
    except Exception as e:
        print(f"[ERROR] search_notes: {e}")
        return False

def get_explore_notes(year=None, branch=None, sem=None, subject=None, q=None):
    # Added error handling for DB fetch
    try:
        base_query = "SELECT * FROM uploaded_files WHERE 1=1"
        params = {}
        if year:
            base_query += " AND year = :year"
            params['year'] = year
        if branch:
            base_query += " AND branch = :branch"
            params['branch'] = branch
        if sem:
            base_query += " AND sem = :sem"
            params['sem'] = sem
        if subject:
            base_query += " AND LOWER(sub_name) LIKE :subject"
            params['subject'] = f"%{subject.lower()}%"
        if q:
            base_query += " AND (LOWER(filename) LIKE :q OR LOWER(sub_name) LIKE :q OR LOWER(description) LIKE :q OR LOWER(unit) LIKE :q)"
            params['q'] = f"%{q.lower()}%"
        query = text(base_query)
        with engine.connect() as conn:
            result = conn.execute(query, params).mappings().all()
        return result if result else []
    except Exception as e:
        print(f"[ERROR] get_explore_notes: {e}")
        return []

def get_user_details(username):
    # Added error handling for DB fetch
    try:
        query = text("SELECT first_name, last_name, branch, username FROM users WHERE username = :username")
        with engine.connect() as conn:
            result = conn.execute(query, {"username": username}).fetchone()
            if result:
                return {
                    "first_name": result[0],
                    "last_name": result[1],
                    "branch": result[2],
                    "username": result[3]
                }
            return None
    except Exception as e:
        print(f"[ERROR] get_user_details: {e}")
        return None

def update_user_details(username, first_name, last_name, branch):
    # Added error handling for DB update
    try:
        query = text("""
            UPDATE users SET first_name = :first_name, last_name = :last_name, branch = :branch
            WHERE username = :username
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {
                "first_name": first_name,
                "last_name": last_name,
                "branch": branch,
                "username": username
            })
            conn.commit()
            return result.rowcount > 0
    except Exception as e:
        print(f"[ERROR] update_user_details: {e}")
        return False
