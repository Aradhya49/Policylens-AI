# PolicyLens – AI Powered Legal Document Analysis Portal

## Overview

PolicyLens is a Flask-based web application that helps users upload and analyze legal documents using AI. The platform provides AI-generated summaries, risk analysis, clause insights, and downloadable reports.


Live Website
https://policylens-ai-1r8t.onrender.com


The project is built using:

* Python (Flask)
* MySQL Database
* HTML/CSS/JavaScript
* AI APIs (Groq / OpenRouter)
* Report Generation using ReportLab

---

# Features

* User Authentication System
* PDF & TXT File Upload
* AI-Based Legal Document Analysis
* Risk Score Generation
* Dashboard for Uploaded Documents
* Downloadable Reports
* Profile Management
* Secure Environment Variable Support

---

# Project Structure

```bash
policylens_FINAL/
│
├── app.py
├── config.py
├── db.py
├── database.sql
├── requirements.txt
├── .env
│
├── routes/
│   ├── auth.py
│   ├── dashboard.py
│   ├── upload.py
│   ├── analysis.py
│   ├── reports.py
│   └── profile.py
│
├── templates/
├── static/
├── uploads/
└── venv/
```

---

# Installation & Setup

## 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/policylens.git
cd policylens
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Mac/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the root folder.

Example:

```env
SECRET_KEY=your_secret_key

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=policylens_db

GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

UPLOAD_FOLDER=uploads
```

---

## 5. Setup MySQL Database

Create a database named:

```sql
policylens_db
```

Then import:

```bash
database.sql
```

---

# Run the Project

```bash
python app.py
```

Application will run on:

```bash
http://127.0.0.1:5001
```

---

# Deployment

## Deploy on Render

### Step 1 — Push Project to GitHub

Initialize Git:

```bash
git init
```

Add files:

```bash
git add .
```

Commit:

```bash
git commit -m "Initial commit"
```

Create GitHub repository and connect:

```bash
git remote add origin https://github.com/YOUR_USERNAME/policylens.git
```

Push:

```bash
git branch -M main
git push -u origin main
```

---

## Step 2 — Deploy on Render

1. Open Render
2. Create New Web Service
3. Connect GitHub Repository
4. Select the repository
5. Configure:

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
python app.py
```

---

# Important Notes

* Do NOT upload your `.env` file to GitHub.
* Add all secret keys inside Render Environment Variables.
* Remove uploaded PDFs from repository before pushing if unnecessary.
* The `venv` folder should not be pushed to GitHub.

---

# Technologies Used

* Flask
* MySQL
* HTML/CSS
* JavaScript
* PyPDF2
* ReportLab
* Requests API
* bcrypt


---

# Author

Aradhya Priya

---

