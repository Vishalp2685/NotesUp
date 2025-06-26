from sqlalchemy import create_engine, text
from datetime import datetime
from rapidfuzz import fuzz
import bcrypt
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload,HttpError
import mimetypes

# If running locally, load from .env
if os.environ.get("RUNNING_IN_DOCKER") != "1":
    from dotenv import load_dotenv
    load_dotenv() 

# Load from actual environment variables
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_name = os.environ.get('DB_NAME')

# Validate
if not all([db_user, db_password, db_host, db_name]):
    raise RuntimeError("Missing DB credentials in environment.")


if db_user and db_password and db_host and db_name:
    DB_URL = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:5432/{db_name}"
else:
    raise RuntimeError("Database credentials are not set in .env. Please set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME.")
engine = create_engine(DB_URL)

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_service_account_info_from_env():
    return {
        "type": os.environ.get("GOOGLE_TYPE"),
        "project_id": os.environ.get("GOOGLE_PROJECT_ID"),
        "private_key_id": os.environ.get("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("GOOGLE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "auth_uri": os.environ.get("GOOGLE_AUTH_URI"),
        "token_uri": os.environ.get("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.environ.get("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.environ.get("GOOGLE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.environ.get("GOOGLE_UNIVERSE_DOMAIN"),
    }

service_account_info = get_service_account_info_from_env()
credentials = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def upload_to_drive(file,file_name):
    try:
        file_metadata = {'name':file_name}
        if os.getenv('FOLDER_ID'):
            file_metadata['parents'] = [os.getenv('FOLDER_ID')]

        # Guess MIME type from file extension
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = 'application/octet-stream'  # fallback

        media = MediaIoBaseUpload(file, mimetype=mime_type)
        
        # file_stream = io.BytesIO(file.read())
        # media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)

        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        file_id = uploaded_file.get('id')
        # view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        return file_id
    except Exception as e:
        print(e)
        return False 
    

def delete_from_drive(file_id):
    try:
        # Attempt to delete the file from Google Drive
        drive_service.files().delete(fileId=file_id).execute()
        print(f"[DELETE SUCCESS] File ID {file_id} deleted from Google Drive.")
        return True

    except HttpError as e:
        print(f"[DELETE ERROR] HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"[DELETE ERROR] {e}")
        return False


def validate(username, password):
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
    


# saving the description in the db generated by AI
def save_summary(uploaded_by,summary,drive_file_path):
    try:
        query = text("""UPDATE uploaded_files
                    SET description = :description
                    WHERE file_path = :file_path AND uploaded_by = :uploaded_by;
                    """)
        params = {
            'description': summary,
            'file_path' :drive_file_path,
            'uploaded_by' :uploaded_by
        }
        with engine.connect() as conn:
            result = conn.execute(query,params)
            conn.commit()
            if result:
                return True
    except Exception as e:
        print(f"[error] while saving the summary : {e}")
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
        query1 = text("SELECT file_path FROM uploaded_files WHERE id = :id")
        with engine.connect() as conn:
            file_path = conn.execute(query1, {"id": id}).fetchone()
        query = text("DELETE FROM uploaded_files WHERE id = :id")
        with engine.connect() as conn:
            result = conn.execute(query,{"id":id})
            conn.commit()
        if file_path and delete_from_drive(file_path[0]):
            deteled = True
        else:
            deteled = False
            print("file deleted from drive")
        if result.rowcount > 0 and deteled:
            print(f"[DELETE SUCCESS] Note with ID {id} deleted from database.")
            return True
        else:
            print(f"[DELETE ERROR] Note with ID {id} not found in database.")
            return False
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
            base_query += " AND (LOWER(sub_name) LIKE :q OR LOWER(description) LIKE :q OR LOWER(unit) LIKE :q)"
            params['q'] = f"%{q.lower()}%"
        query = text(base_query)
        with engine.connect() as conn:
            result = conn.execute(query, params).mappings().all()
        return result if result else []
    except Exception as e:
        print(f"[ERROR] get_explore_notes: {e}")
        return []

def get_user_details(username):
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

def save_note_for_user(user_id, note_id):
    """Save a note for a user. Returns True if saved, False if already saved or error."""
    try:
        query = text("""
            INSERT INTO user_saved_notes (user_id, note_id)
            VALUES (:user_id, :note_id)
            ON CONFLICT (user_id, note_id) DO NOTHING;
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id, "note_id": note_id})
            conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] save_note_for_user: {e}")
        return False

def unsave_note_for_user(user_id, note_id):
    """Unsave a note for a user. Returns True if unsaved, False if not found or error."""
    try:
        query = text("""
            DELETE FROM user_saved_notes WHERE user_id = :user_id AND note_id = :note_id
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id, "note_id": note_id})
            conn.commit()
        return True
    except Exception as e:
        print(f"[ERROR] unsave_note_for_user: {e}")
        return False

def is_note_saved_by_user(user_id, note_id):
    """Check if a note is saved by a user. Returns True/False."""
    try:
        query = text("""
            SELECT 1 FROM user_saved_notes WHERE user_id = :user_id AND note_id = :note_id
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id, "note_id": note_id}).fetchone()
        return bool(result)
    except Exception as e:
        print(f"[ERROR] is_note_saved_by_user: {e}")
        return False

def get_saved_notes_for_user(user_id):
    """Get all notes saved by a user. Returns a list of note IDs."""
    try:
        query = text("""
            SELECT note_id FROM user_saved_notes WHERE user_id = :user_id
        """)
        with engine.connect() as conn:
            result = conn.execute(query, {"user_id": user_id}).fetchall()
        return [row[0] for row in result]
    except Exception as e:
        print(f"[ERROR] get_saved_notes_for_user: {e}")
        return []

def get_user_id(username):
    """Get the user id for a given username. Returns user id or None."""
    try:
        query = text("SELECT id FROM users WHERE username = :username")
        with engine.connect() as conn:
            result = conn.execute(query, {"username": username}).fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"[ERROR] get_user_id: {e}")
        return None

