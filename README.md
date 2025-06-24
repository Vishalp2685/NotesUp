# Notes Sharing Platform

A collaborative platform for students to upload, search, and share academic notes.

## Features
- Upload notes (PDF, DOC, PPT, etc.) with subject, branch, semester, and year fields
- Automatic generation of concise descriptions for notes
- Google Drive integration for file storage
- Advanced search and filtering

## Setup Instructions

### 1. Clone the repository
```
git clone https://github.com/yourusername/notes-sharing-platform.git
cd notes-sharing-platform
```

### 2. Install dependencies
```
pip install -r requirements.txt
```

### 3. Google Drive API Setup

- Go to [Google Cloud Console](https://console.cloud.google.com/).
- Create a new project (or select an existing one).
- Enable the **Google Drive API** for your project.
- Create a **Service Account** and download the `service_account.json` file.
- Place the `service_account.json` file in the root directory of your project.
- Share your target Google Drive folder with the service account email (found in the `service_account.json`).

### 4. Environment Variables

- Copy `.env.example` to `.env`:
  ```
  cp .env.example .env
  ```
- Fill in your secret key and database credentials in `.env`:
  ```
  SECRET_KEY=your_flask_secret_key
  DB_USER=your_db_user
  DB_PASSWORD=your_db_password
  DB_HOST=your_db_host
  DB_NAME=your_db_name
  FOLDER_ID=your_google_drive_folder_id
  ```

### 5. Database Setup

- Ensure you have a PostgreSQL database running.
- Create the required tables (`users`, `uploaded_files`, `user_saved_notes`) as per your schema.
- Update the `.env` file with your database credentials.

### 6. Run the Application

```
python app.py
```
- The app will be available at `http://127.0.0.1:5000/`

## Contributing
Pull requests are welcome!
---
