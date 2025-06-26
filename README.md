# NotesUp

NotesUp is a collaborative platform for students to upload, share, and explore academic notes. It features AI-generated descriptions for uploaded files, Google Drive integration, and a modern, user-friendly interface.

## Features
- User registration and login
- Upload multiple notes (PDF, DOC, DOCX, PPT, PPTX)
- AI-generated note descriptions
- Google Drive integration for file storage
- Explore, search, and save notes
- Dashboard for managing uploaded and saved notes
- Secure password requirements
- Dockerized deployment

## Tech Stack
- Python 3.12
- Flask
- SQLAlchemy
- Google Drive API
- Gunicorn
- Docker & Docker Compose
- HTML/CSS/JavaScript (frontend)

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Google Cloud project with Drive API enabled (for file storage)
- Python 3.12 (for local development)

### Environment Variables
Create a `.env` file in the project root with the following variables:
```
SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_api_key
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_NAME=your_db_name
FOLDER_ID=your_google_drive_folder_id
GOOGLE_TYPE=service_account
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_PRIVATE_KEY_ID=your_private_key_id
GOOGLE_PRIVATE_KEY=your_private_key
GOOGLE_CLIENT_EMAIL=your_client_email
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
GOOGLE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GOOGLE_CLIENT_X509_CERT_URL=your_client_x509_cert_url
GOOGLE_UNIVERSE_DOMAIN=googleapis.com
```

### Build & Run with Docker
1. Build and start the app:
   ```sh
   docker compose up --build
   ```
2. The app will be available at [http://localhost:8000](http://localhost:8000)

### Local Development (without Docker)
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Set environment variables (see above).
3. Run the app:
   ```sh
   python app.py
   ```

## Usage
- Register a new account and log in.
- Upload notes (max 10 files at a time, max 30MB each).
- Explore and save notes from other users.
- AI will generate descriptions for your notes in the background.

## Security Notes
- Passwords must be strong (min 8 chars, upper/lowercase, number, special char).
- Uploaded files are stored in Google Drive; temp files are cleaned up after processing.

## Troubleshooting
- If you see a warning about session cookie size, reduce what you store in the session.
- If uploads fail, check that the `temp` directory exists and is writable.
- For Google Drive issues, verify your service account credentials and permissions.

## License
MIT License

---

**Contributions are welcome!**
