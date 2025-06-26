from flask import Flask,render_template,request,redirect,url_for,session,flash
import database as db
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory,abort
import re
from flask import g
import generate_summary
import threading
from sqlalchemy import text as sa_text

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

def add_user(first_name,last_name,branch,user_name,password):
    user = db.register_user(first_name=first_name,last_name=last_name,branch=branch,username=user_name,password=password)
    return user

def sanitize_input(value):
    if value is None:
        return None
    value = re.sub(r"[;'\"]", "", value) 
    value = value.strip()
    return value

@app.route('/sign-up',methods = ['POST','GET'])
def sign_up():
    try:
        if request.method == 'GET':
            # Clear flashed messages before rendering sign up page
            # session.pop('_flashes', None)
            return render_template('sign_up.html')
        password = request.form.get('password')
        re_pass = request.form.get('re_pass')
        if password == re_pass:
            first_name = sanitize_input(request.form.get('first_name'))
            last_name = sanitize_input(request.form.get('last_name'))
            branch = sanitize_input(request.form.get('branch'))
            user_name = sanitize_input(request.form.get('user_name'))
            save_in_database = add_user(first_name,last_name,branch,user_name,password)
            if save_in_database:
                flash('User registered successfully', 'success')
                return redirect(url_for('login'))
            else:
                flash('database error occurred or user already exists', 'error')
                return redirect(url_for('sign_up'))
        else:
            flash('Passwords do not match', 'error')
            return render_template('sign_up.html')
    except Exception as e:
        flash(f'Unexpected error: {e}', 'error')
        return render_template('sign_up.html')    
    
semaphore = threading.Semaphore(2)  # Allow only 2 threads at a time

def safe_summary_worker(*args):
    with semaphore:
        background_summary_worker(*args)


def background_summary_worker(uploaded_by, filename, local_path,file_path):
    try:
        print("text_generation started for",filename)
        text = generate_summary.extract_text_from_file(local_path)
        print(f"text generation completed for {filename} and starting summary generation")
        summary = generate_summary.generate_description_from_text(text)
        db.save_summary(uploaded_by,summary,file_path)
        print(f"Summary generated for {filename} and saving to database")
        os.remove(local_path)  # Clean up temp file
        print(f"Temporary file {local_path} removed")
        print(f"[INFO] Summary generated and saved for {filename}")
    except Exception as e:
        print(f"[ERROR] Summary generation failed for {filename}: {e}")



@app.route('/upload',methods=['GET','POST'])
def upload():
    try:
        if request.method == 'GET':
            if 'login' in session:
                return render_template('upload.html')
            else:
                return redirect(url_for('login'))
        else:
            if 'dashboard' in request.form:
                return redirect(url_for('dashboard'))
            elif 'home' in request.form:
                return redirect(url_for('home'))
            elif 'explore' in request.form:
                return redirect(url_for('explore'))
            elif 'logout' in request.form:
                session.clear()
                return redirect(url_for('login')) 
            elif 'upload' in request.form:
                return redirect(url_for('upload'))
            else:
                sub_name = sanitize_input(request.form.get('subject'))
                branch = sanitize_input(request.form.get('branch'))
                sem = sanitize_input(request.form.get('semester'))
                year = sanitize_input(request.form.get('year'))
                desc = sanitize_input(request.form.get('description'))
                files = request.files.getlist('files')
                units = []
                if desc:
                    generate_summary = False
                else:
                    generate_summary =True
                for idx in range(len(files)):
                    unit = request.form.get(f'unit_for_file_{idx}')
                    units.append(unit)
                
                for i, file in enumerate(files):
                    if file:
                        filename = secure_filename(file.filename)
                        temp_path = os.path.join("temp", filename)
                        file.save(temp_path)
                        with open(temp_path,'rb') as f:
                            file_path = db.upload_to_drive(f,file_name=filename)
                        print(f"filepath{file_path}")
                        if not file_path:
                            print('File upload to Google Drive failed', 'upload_error')
                            # flash('File upload to Google Drive failed') # Upload to Google Drive and get link
                            return redirect(url_for('upload'))
                        if not db.file_data(session['username'], sub_name, branch, sem, year, desc, units[i], filename, file_path):
                            print('Database error occurred', 'upload_error')
                            flash('Database error occurred while saving file data', 'upload_error')
                            return redirect(url_for('upload'))
                        if generate_summary:
                        # Background summary generation thread
                            thread = threading.Thread(
                                target=safe_summary_worker,
                                args=(session['username'], filename, temp_path,file_path)
                            )
                            thread.start()
                    else:
                        # flash('No file selected', 'upload_error')
                        print('No file selected', 'upload_error')
                        return redirect(url_for('upload'))
                    # download  the file from drive to genrate description
                print('Files uploaded successfully', 'success')
                flash('Files uploaded successfully', 'upload_success')
                return redirect(url_for('upload'))
    except Exception as e:
        # flash(f'Unexpected error: {e}', 'error')
        return redirect(url_for('upload'))

@app.route('/explore', methods=['GET', 'POST'])
def explore():
    try:
        if request.method == 'GET':
            year = sanitize_input(request.args.get('year', '')) or None
            branch = sanitize_input(request.args.get('branch', '')) or None
            sem = sanitize_input(request.args.get('sem', '')) or None
            subject = sanitize_input(request.args.get('subject', '')) or None
            if session.get('search_query'):
                q = sanitize_input(session['search_query']) or None
                session.pop('search_query', None)  # Clear search query after use
            else:
                q = sanitize_input(request.args.get('q', '')) or None
            notes = db.get_explore_notes(year=year, branch=branch, sem=sem, subject=subject, q=q)
            notes = notes[::-1]
            if not year and not branch and not sem and not subject and not q:
                notes = notes[:10]
            formatted_notes = []
            user_id = session.get('user_id')
            saved_note_ids = set()
            if user_id:
                saved_note_ids = set(db.get_saved_notes_for_user(user_id) or [])
            for row in notes:
                row_dict = dict(row)
                if 'uploaded_at' in row_dict and row_dict['uploaded_at']:
                    row_dict['uploaded_at'] = row_dict['uploaded_at'].isoformat() if hasattr(row_dict['uploaded_at'], 'isoformat') else row_dict['uploaded_at']
                if 'file_path' in row_dict:
                    row_dict['file_path'] = row_dict['file_path'].replace('\\', '/').replace('\\', '/')
                if user_id:
                    row_dict['is_saved'] = row_dict['id'] in saved_note_ids
                else:
                    row_dict['is_saved'] = False
                formatted_notes.append(row_dict)
            return render_template('explore.html', notes=formatted_notes)
        else:
            req_form = request.form
            if 'home' in req_form:
                return redirect(url_for('home'))
            elif 'explore' in req_form:
                return redirect(url_for('explore'))
            elif 'dashboard' in req_form:
                return redirect(url_for('dashboard'))
            elif 'logout' in req_form:
                session.clear()
                return redirect(url_for('login'))
            elif 'upload' in req_form:
                return redirect(url_for('upload'))
            else:
                session.clear()
                return redirect(url_for('login'))
    except Exception as e:
        # flash(f'Error loading explore page: {e}', 'explore_error')
        return render_template('explore.html', notes=[])

@app.route('/dashboard',methods = ['GET','POST'])
def dashboard():
    if not session.get("login"):
        return redirect(url_for("login"))

    try:
        if request.method == 'GET':
            if 'login' in session:
                data = db.get_dashbard_details(session['username'])
                if data:
                    data = data[::-1]
            else:
                return redirect(url_for('login'))
            details = []
            user_id = session.get('user_id')
            saved_note_ids = set()
            if user_id:
                saved_note_ids = set(db.get_saved_notes_for_user(user_id) or [])
            if data:
                for row in data:
                    row_dict = dict(row)
                    row_dict['uploaded_at'] = row_dict['uploaded_at'].isoformat()
                    row_dict['file_path'] = row_dict['file_path'].replace('\\','/')
                    details.append(row_dict)
                session['details'] = details
            else:
                session['details'] = []
            user_details = db.get_user_details(session['username'])
            # Fetch all saved notes for the user in a single query
            saved_notes = []
            if user_id and saved_note_ids:
                # Fetch all note details in a single query for all saved_note_ids
                if saved_note_ids:
                    placeholders = ','.join([':id'+str(i) for i in range(len(saved_note_ids))])
                    params = {('id'+str(i)): note_id for i, note_id in enumerate(saved_note_ids)}
                    query = f"SELECT * FROM uploaded_files WHERE id IN ({placeholders})"
                    with db.engine.connect() as conn:
                        result = conn.execute(sa_text(query), params).mappings().all()
                    for note_row in result:
                        note_dict = dict(note_row)
                        if 'uploaded_at' in note_dict and note_dict['uploaded_at']:
                            note_dict['uploaded_at'] = note_dict['uploaded_at'].isoformat() if hasattr(note_dict['uploaded_at'], 'isoformat') else note_dict['uploaded_at']
                        if 'file_path' in note_dict:
                            note_dict['file_path'] = note_dict['file_path'].replace('\\', '/')
                        saved_notes.append(note_dict)
            return render_template('dashboard.html', user_details=user_details, saved_notes=saved_notes)
        else:
            req_form = request.form
            if 'home' in req_form:
                return redirect(url_for('home'))
            elif 'explore' in req_form:
                return redirect(url_for('explore'))
            elif 'dashboard' in req_form:
                return redirect(url_for('dashboard'))
            elif 'logout' in req_form:
                session.clear()
                return redirect(url_for('login'))
            elif 'upload' in req_form:
                return redirect(url_for('upload'))
    except Exception as e:
        # flash(f'Error loading dashboard: {e}', 'error')
        print(f'Error loading dashboard: {e}')
        return redirect(url_for('dashboard'))

@app.route('/delete/<int:id>',methods = ['POST'])
def delete(id):
    try:
        if 'delete' in request.form:
            a = db.delete(id)
            if a:
                print("file deleted with id",id)
            else:
                print("failed to delete file")
        return redirect(url_for('dashboard'))
    except Exception as e:
        # flash(f'Error deleting file: {e}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/login',methods = ['POST','GET'])
def login():
    try:
        if request.method == 'GET':
            # Clear flashed messages before rendering login page
            return render_template('login.html')
        else:
            if 'sign-up' in request.form:
                return redirect(url_for('sign_up'))
            user_name = request.form.get('user_name').strip()
            password = request.form.get('password').strip()
            user = db.validate(username=user_name,password=password)
            if user:
                session['login'] = True
                session['profile_logo'] = user['first_name'][0] + user['last_name'][0]
                session['username'] = user_name
                # Set user_id in session for save/unsave logic
                user_id = db.get_user_id(user_name)
                session['user_id'] = user_id
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
                return redirect(url_for('login'))
    except Exception as e:
        flash(f'Login error, Please try again', 'error')
        return redirect(url_for('login'))

@app.route('/',methods = ['GET','POST'])
def home():
    try:
        if request.method == 'GET':
            return render_template('home.html')
        else:
            req_form = request.form
            if 'upload' in req_form:
                if 'login' in session:
                    return redirect(url_for('upload'))
                else:
                    return redirect(url_for('login'))
            elif 'dashboard' in req_form:
                if 'login' in session:
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(url_for('login'))
            elif 'home' in req_form:
                return render_template('home.html')
            elif 'explore' in req_form:
                return redirect(url_for('explore'))
            elif 'login' in req_form:
                return redirect(url_for('login'))
            elif 'logout' in req_form:
                session.clear()
                return redirect(url_for('home'))
            elif 'q' in req_form:
                search_query = sanitize_input(request.form.get('q'))
                session['search_query'] = search_query
                return redirect(url_for('explore'))
            else:
                return render_template('home.html')
    except Exception as e:
        return render_template('home.html')

@app.route('/save_note/<int:note_id>', methods=['POST'])
def save_note(note_id):
    try:
        user_id = session.get('user_id') or getattr(g, 'user_id', None)
        if not user_id:
            return redirect(url_for('login'))
        else:
            db.save_note_for_user(user_id, note_id)
            print(request.args.get("q"))
        return redirect(request.referrer or url_for('explore'))
    except Exception as e:
        return redirect(request.referrer or url_for('explore'))

@app.route('/unsave_note/<int:note_id>', methods=['POST'])
def unsave_note(note_id):
    try:
        user_id = session.get('user_id') or getattr(g, 'user_id', None)
        if not user_id:
            return redirect(request.referrer or url_for('explore'))
        if db.is_note_saved_by_user(user_id, note_id):
            db.unsave_note_for_user(user_id, note_id)
        return redirect(request.referrer or url_for('explore'))
    except Exception as e:
        return redirect(request.referrer or url_for('explore'))

if __name__ == '__main__':
    app.run()