# Employee Track Report – Employee Progress Tracker

A modern Streamlit dashboard with AI-powered chatbot, attendance tracking, task management, and automated reminders.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Features
- Interactive Streamlit dashboard
- AI Chatbot (powered by Groq + Hugging Face)
- Real-time attendance tracking
- Task assignment & progress monitoring
- Automated reminders
- Jira integration (optional)
- Works locally and in production

## Quick Start (Local)

```bash
# Clone the repo
git clone https://github.com/SoumyaR01/Employee-Task-Tracker.git
cd Employee-Task-Tracker

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy example env and fill your keys
cp .env.example .env
# Edit .env with your real API keys

# Run the app
streamlit run main.py

App will be available at: http://localhost:8501
Deployment Options
Option 1: Render.com (Recommended for Production)
Render supports Docker + persistent storage → perfect for Excel/CSV persistence.
Steps:

Push code to GitHub
Go to render.com → New → Web Service
Connect your GitHub repo → Select branch
Choose Docker as runtime
Add Environment Variables:

GROQ_API_KEY = your_groq_key
HuggingFaceAPIKey = your_hf_token
InputLanguage = en

Add a Persistent Disk:
Mount Path: /app/Data
Size: 1 GB (or more)

Deploy!

Your files (task_tracker.xlsx, attendance_records.csv, etc.) will now live safely inside /app/Data/
Option 2: Streamlit Community Cloud (Free & Fast)
Limitations: No persistent local files
How to make it work:
Replace local Excel/CSV storage with one of these:

Google Sheets + gspread (recommended)
MongoDB Atlas
PostgreSQL (Render / Supabase / Neon)

We provide a Google Sheets version in the streamlit-cloud-branch if you want zero-cost hosting.
Option 3: GitHub Codespaces (Best for Development)
Just click Code → Codespaces → Create codespace on main
The app auto-starts on port 8501 with everything pre-installed!

Project Structure
├── main.py                  # Streamlit dashboard
├── EmployeeChatBot.py       # AI assistant
├── attendance_store.py      # Attendance logic
├── reminder_service.py      # Reminder engine
├── Data/                    # ← All persistent files go here
│   ├── task_tracker.xlsx
│   ├── attendance_records.csv
│   ├── employees.json
│   └── config.json
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── .env.example             # Never commit real keys!

Secrets & Environment Variables
Use .env locally → Secrets on Streamlit Cloud → Environment Variables on Render
GROQ_API_KEY=gsk_...
HuggingFaceAPIKey=hf_...
InputLanguage=en

# Optional Jira
JIRA_URL=https://your.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your_token
JIRA_DEFAULT_PROJECT=SCRUM

Docker Support
# Build
docker build -t employee-tracker .

# Run locally
docker run -p 8501:8501 --env-file .env employee-tracker

Future Improvements (Production-Ready Path)
Feature,Current,Recommended Upgrade
Data Storage,Excel/CSV,PostgreSQL / MongoDB
File Persistence,Local disk,Cloud storage / Database
Concurrent Users,Single file,Database with locking
Backups,Manual,Automated (S3 / Backblaze)
Authentication,None,Streamlit-Authenticator / OAuth

Contributing
Pull requests are welcome! For major changes, please open an issue first.
License
MIT License – feel free to use, modify, and deploy.

Made with Streamlit | Deployed with Render | Powered by Groq & HF


This README looks professional, renders beautifully on GitHub, and helps anyone (or future you) deploy the app in under 5 minutes.

Just replace your current `README.md` with this, commit, and you’re good to go!
