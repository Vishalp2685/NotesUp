from flask import Flask,render_template,request,redirect,url_for,session,flash,jsonify
import database as db
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory,abort
import re
from flask import g
# Remove hardcoded secret key and use environment variable
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
            session.pop('_flashes', None)
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
                for idx in range(len(files)):
                    unit = request.form.get(f'unit_for_file_{idx}')
                    units.append(unit)
                for i, file in enumerate(files):
                    if file:
                        filename = secure_filename(file.filename)
                        file_path = db.upload_to_drive(file,file_name=filename)
                        if not file_path:
                            print('File upload to Google Drive failed', 'upload_error')
                            flash('File upload to Google Drive failed') # Upload to Google Drive and get link
                            return redirect(url_for('upload'))
                        if not db.file_data(session['username'], sub_name, branch, sem, year, desc, units[i], filename, file_path):
                            print('Database error occurred', 'upload_error')
                            flash('Database error occurred while saving file data', 'upload_error')
                            return redirect(url_for('upload'))
                    else:
                        flash('No file selected', 'upload_error')
                        print('No file selected', 'upload_error')
                        return redirect(url_for('upload'))
                print('Files uploaded successfully', 'success')
                flash('Files uploaded successfully', 'upload_success')
                return redirect(url_for('upload'))
    except Exception as e:
        flash(f'Unexpected error: {e}', 'error')
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
                q = session['search_query']
                session.pop('search_query', None)  # Clear search query after use
                print("session notes ")
            else:
                q = sanitize_input(request.args.get('q', '')) or None
            print(f"Explore page accessed with year={year}, branch={branch}, sem={sem}, subject={subject}, q={q}")
            notes = db.get_explore_notes(year=year, branch=branch, sem=sem, subject=subject, q=q)
            notes = notes[::-1]
            print(f"Retrieved {len(notes)} notes from the database")
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
    except Exception as e:
        flash(f'Error loading explore page: {e}', 'explore_error')
        return render_template('explore.html', notes=[])

@app.route('/dashboard',methods = ['GET','POST'])
def dashboard():
    try:
        if request.method == 'GET':
            if 'login' in session:
                data = db.get_dashbard_details(session['username'])
                if data:
                    data = data[::-1]
            else:
                return redirect(url_for('login'))
            details = []
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
            # Fetch saved notes for the user
            user_id = session.get('user_id')
            saved_notes = []
            if user_id:
                saved_note_ids = db.get_saved_notes_for_user(user_id)
                if saved_note_ids:
                    # Fetch note details for each saved note id
                    for note_id in saved_note_ids:
                        note_row = db.get_note_by_id(note_id)
                        if note_row:
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
        flash(f'Error deleting file: {e}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/login',methods = ['POST','GET'])
def login():
    try:
        if request.method == 'GET':
            # Clear flashed messages before rendering login page
            session.pop('_flashes', None)
            return render_template('login.html')
        else:
            if 'sign-up' in request.form:
                return redirect(url_for('sign_up'))
            user_name = request.form.get('user_name')
            password = request.form.get('password')
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
        flash(f'Login error: {e}', 'error')
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
            
    except Exception as e:
        flash(f'Error loading home page: {e}', 'error')
        return render_template('home.html')

@app.route('/save_note/<int:note_id>', methods=['POST'])
def save_note(note_id):
    try:
        user_id = session.get('user_id') or getattr(g, 'user_id', None)
        if not user_id:
            flash('You must be logged in to save notes.', 'error')
            return redirect(request.referrer or url_for('explore'))
        if db.is_note_saved_by_user(user_id, note_id):
            flash('Note already saved.', 'error')
        else:
            db.save_note_for_user(user_id, note_id)
            flash('Note saved!', 'success')
        return redirect(request.referrer or url_for('explore'))
    except Exception as e:
        flash(f'Error saving note: {e}', 'error')
        return redirect(request.referrer or url_for('explore'))

@app.route('/unsave_note/<int:note_id>', methods=['POST'])
def unsave_note(note_id):
    try:
        user_id = session.get('user_id') or getattr(g, 'user_id', None)
        if not user_id:
            flash('You must be logged in to unsave notes.', 'error')
            return redirect(request.referrer or url_for('explore'))
        if db.is_note_saved_by_user(user_id, note_id):
            db.unsave_note_for_user(user_id, note_id)
            flash('Note unsaved.', 'success')
        else:
            flash('Note was not saved.', 'error')
        return redirect(request.referrer or url_for('explore'))
    except Exception as e:
        flash(f'Error unsaving note: {e}', 'error')
        return redirect(request.referrer or url_for('explore'))

if __name__ == '__main__':
    app.run(debug=True)