from sqlalchemy import create_engine, text
from datetime import datetime
from rapidfuzz import fuzz
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Compose DB URL from .env variables if NOTESHUB_DB_URL is not set

db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_name = os.environ.get('DB_NAME')
if db_user and db_password and db_host and db_name:
    DB_URL = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:3306/{db_name}?charset=utf8mb4"
else:
    raise RuntimeError("Database credentials are not set in .env. Please set NOTESHUB_DB_URL or DB_USER, DB_PASSWORD, DB_HOST, DB_NAME.")
engine = create_engine(DB_URL)

def validate(username, password):
    query = text("SELECT first_name, last_name, password FROM users WHERE username = :username")
    with engine.connect() as conn:
        result = conn.execute(query, {"username": username}).fetchone()
        if result:
            stored_hash = result[2]
            # Check if the stored password is a bcrypt hash
            if stored_hash.startswith("$2a$") or stored_hash.startswith("$2b$"):
                if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                    return {'first_name': result[0], 'last_name': result[1]}  # Return as dict for attribute access
                else:
                    return None
            else:
                # Not a bcrypt hash, likely legacy/invalid password
                # Optionally, you can log this or trigger a password reset
                print("[SECURITY] User has non-bcrypt password hash. Password reset required.")
                return None
        return None

def register_user(first_name, last_name, username, password, branch):
    already_exist = text("""
                SELECT * FROM users WHERE username = :username
                         """)
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
    

def file_data(uploaded_by, sub_name, branch, sem, year, desc, tags, filename, file_path):
    query = text("""
        INSERT INTO uploaded_files (
            uploaded_by, sub_name, branch, sem, year, description, tags, filename, file_path, uploaded_at
        ) VALUES (
            :uploaded_by, :sub_name, :branch, :sem, :year, :description, :tags, :filename, :file_path, :uploaded_at
        )
    """)

    params = {
        'uploaded_by': uploaded_by,
        'sub_name': sub_name,
        'branch': branch,
        'sem': sem,
        'year': year,
        'description': desc,
        'tags': tags,
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
    

def get_dashbard_details(user_name):
    query = text("SELECT * FROM uploaded_files WHERE uploaded_by = :username")
    with engine.connect() as conn:
        result = conn.execute(query,{"username":user_name}).mappings().all()
    return result if result else False


def delete(id):
    query = text("DELETE FROM uploaded_files WHERE id = :id")
    with engine.connect() as conn:
        result = conn.execute(query,{"id":id})
        conn.commit()
    print("file deleted")
    return True if result else False


def search_notes(search_query):
    # Improved search: partial match on subject, description, tags, and filename
    like_query = f"%{search_query}%"
    query = text("""
        SELECT * FROM uploaded_files
        WHERE sub_name LIKE :q
           OR description LIKE :q
           OR tags LIKE :q
           OR filename LIKE :q
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"q": like_query}).mappings().all()
    if result:
        # Optionally, sort by fuzzy match score for better ranking
        result = sorted(result, key=lambda row: max(
            fuzz.partial_ratio(search_query.lower(), str(row['sub_name']).lower()),
            fuzz.partial_ratio(search_query.lower(), str(row['description']).lower()),
            fuzz.partial_ratio(search_query.lower(), str(row['tags']).lower()),
            fuzz.partial_ratio(search_query.lower(), str(row['filename']).lower())
        ), reverse=True)
        return result
    return False

def get_explore_notes(year=None, branch=None, sem=None, subject=None, q=None):
    """
    Fetch notes for the explore page with optional filters and search.
    All params are strings or None.
    """
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
        base_query += " AND (LOWER(filename) LIKE :q OR LOWER(sub_name) LIKE :q OR LOWER(description) LIKE :q OR LOWER(tags) LIKE :q)"
        params['q'] = f"%{q.lower()}%"
    query = text(base_query)
    with engine.connect() as conn:
        result = conn.execute(query, params).mappings().all()
    return result if result else []

def get_user_details(username):
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