from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import os
app = Flask(__name__)

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'service_account.json'
# FOLDER_ID = '16MnPZcridcMhtDFv8Ohtn4CfFvL48xIm'  # Optional, leave empty if not using a folder

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

@app.route('/upload', methods=['POST'])
def upload_to_drive():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_metadata = {'name': file.filename}
    if os.getenv('FOLDER_ID'):
        file_metadata['parents'] = os.getencv('FOLDER_ID')

    file_stream = io.BytesIO(file.read())
    media = MediaIoBaseUpload(file_stream, mimetype=file.content_type)

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')
    view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    return jsonify({"file_id": file_id, "view_link": view_link})



# def upload(file_name):
#     file_metadata = {'name': file_name}
#     if FOLDER_ID:
#         file_metadata['parents'] = [FOLDER_ID]
#     file = open(file_name, 'rb')  # Open the file in binary mode
#     file_stream = io.BytesIO(file.read())
#     media = MediaIoBaseUpload(file_stream, mimetype='txt/plain', resumable=True)

#     uploaded_file = drive_service.files().create(
#         body=file_metadata,
#         media_body=media,
#         fields='id'
#     ).execute()

#     file_id = uploaded_file.get('id')
#     view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

#     return {"file_id": file_id, "view_link": view_link}


# print(upload('test.txt'))  # Replace 'test.txt' with the actual file object you want to upload