from flask import Flask,render_template,request,redirect,url_for,session,flash
import database as db
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory,abort
import re

# Remove hardcoded secret key and use environment variable
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'changeme-in-production')

def add_user(first_name,last_name,branch,user_name,password):
    user = db.register_user(first_name=first_name,last_name=last_name,branch=branch,username=user_name,password=password)
    return user

def sanitize_input(value):
    if value is None:
        return None
    value = re.sub(r"[;'\"]", "", value) 
    value = value.strip()
    return value

# --- Error handling added throughout this file ---

@app.route('/sign-up',methods = ['POST','GET'])
def sign_up():
    try:
        if request.method == 'GET':
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

@app.route('/search/<string:resource>', methods=['GET', 'POST'])
def search_page(resource):
    try:
        resource = sanitize_input(resource)
        if request.method == 'GET':
            found_resources = db.search_notes(resource)
            resources = []
            if found_resources:
                for row in found_resources:
                    row_dict = dict(row)
                    row_dict['uploaded_at'] = row_dict['uploaded_at'].isoformat()
                    row_dict['file_path'] = row_dict['file_path'].replace('\\','/')
                    resources.append(row_dict)
                    session['resources'] = resources
            return render_template('search.html', notes=resources, query=resource)
        # POST form handling
        if request.form.get('upload'):
            return redirect(url_for('upload'))
        elif request.form.get('login'):
            return redirect(url_for('login'))
        elif 'logout' in request.form:
            session.clear()
            return redirect(url_for('login'))
        elif request.form.get('search-query'):
            new_query = sanitize_input(request.form.get('search-query'))
            found_resources = db.search_notes(new_query)
            resources = []
            if found_resources:
                for row in found_resources:
                    row_dict = dict(row)
                    row_dict['uploaded_at'] = row_dict['uploaded_at'].isoformat()
                    row_dict['file_path'] = row_dict['file_path'].replace('\\','/')
                    resources.append(row_dict)
                    session['resources'] = resources
            return render_template('search.html', notes=resources, query=resource)
        return redirect(url_for('search_page', resource=resource))
    except Exception as e:
        flash(f'Error loading search page: {e}', 'error')
        return render_template('search.html', notes=[], query=resource)

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
                        file_path = os.path.join('static/uploads', filename)
                        try:
                            file.save(file_path)
                        except Exception as e:
                            flash(f'File save error: {e}', 'error')
                            continue
                        if db.file_data(session['username'], sub_name, branch, sem, year, desc, units[i], filename, file_path):
                            flash('File successfully uploaded')
                        else:
                            flash('Database error occurred', 'error')
                    else:
                        flash('No file selected', 'error')
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
            q = sanitize_input(request.args.get('q', '')) or None
            notes = db.get_explore_notes(year=year, branch=branch, sem=sem, subject=subject, q=q)
            notes = notes[::-1]
            formatted_notes = []
            for row in notes:
                row_dict = dict(row)
                if 'uploaded_at' in row_dict and row_dict['uploaded_at']:
                    row_dict['uploaded_at'] = row_dict['uploaded_at'].isoformat() if hasattr(row_dict['uploaded_at'], 'isoformat') else row_dict['uploaded_at']
                if 'file_path' in row_dict:
                    row_dict['file_path'] = row_dict['file_path'].replace('\\', '/').replace('\\', '/')
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
        flash(f'Error loading explore page: {e}', 'error')
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
            return render_template('dashboard.html', user_details=user_details)
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
                flash('Unknown dashboard action', 'error')
                return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'error')
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
            elif 'search-query' in req_form:
                new_query = req_form.get('search-query')
                found_resources = db.search_notes(new_query)
                resources = []
                if found_resources:
                    for row in found_resources:
                        row_dict = dict(row)
                        row_dict['uploaded_at'] = row_dict['uploaded_at'].isoformat()
                        row_dict['file_path'] = row_dict['file_path'].replace('\\','/')
                        resources.append(row_dict)
                        session['resources'] = resources
                return render_template('search.html', notes=resources, query=new_query)
    except Exception as e:
        flash(f'Error loading home page: {e}', 'error')
        return render_template('home.html')

@app.route('/download/file/<path:filepath>')
def download_any_file(filepath):
    try:
        # Only allow files from known safe directories
        allowed_dirs = [
            os.path.join(os.getcwd(), 'engineering_notes'),
            os.path.join(os.getcwd(), 'static', 'uploads'),
            os.path.join(os.getcwd(), 'static')
        ]
        abs_path = os.path.abspath(os.path.join(os.getcwd(), filepath))
        for allowed in allowed_dirs:
            if abs_path.startswith(allowed):
                directory, filename = os.path.split(abs_path)
                # For PDF preview, set as_attachment=False for inline viewing
                if filename.lower().endswith('.pdf') and request.args.get('preview') == '1':
                    if not os.path.exists(os.path.join(directory, filename)):
                        abort(404)  # File not found
                    return send_from_directory(directory, filename, as_attachment=False)
                if not os.path.exists(os.path.join(directory, filename)):
                    abort(404)  # File not found
                return send_from_directory(directory, filename, as_attachment=True)
        abort(404)
    except Exception as e:
        flash(f'File download error: {e}', 'error')
        abort(404)

if __name__ == '__main__':
    app.run(debug=True)