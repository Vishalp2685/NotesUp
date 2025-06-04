# Notes Sharing Platform

A collaborative platform for students to upload, search, and share academic notes.

## Features
- Upload notes (PDF, DOC, PPT, etc.) with subject, branch, semester, and year fields
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

### 3. Create a `.env` file
- Copy `.env.example` or create `.env` manually:
  ```
  cp .env.example .env
  ```
- Add your `SECRET_KEY` and any DB credentials.

### 4. Run the Application
```
python app.py
```
- The app will be available at `http://127.0.0.1:5000/`

## Contributing
Pull requests are welcome!
---
