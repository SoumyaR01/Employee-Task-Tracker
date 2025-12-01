🚀 Employee Track Report – Deployment Guide

A simple and clear guide to containerize and deploy your Employee Progress Tracker app using Docker on Render, Streamlit Cloud and GitHub Codespaces.

📌 Project Overview

Your app includes:

main.py – Streamlit dashboard

EmployeeChatBot.py – AI chatbot

attendance_store.py – Attendance tracking

reminder_service.py – Reminder engine

Storage files – Excel, CSV, and JSON configs

🐳 Docker Setup
1. Dockerfile

Create a Dockerfile in your project folder:

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p Data logo

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

2. .dockerignore

Avoid pushing unnecessary files:

.venv
__pycache__
*.pyc
.git
.env
.vscode
.idea
*.md

3. docker-compose (Optional)
version: "3.8"

services:
  employee-tracker:
    build: .
    ports:
      - "8501:8501"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - HuggingFaceAPIKey=${HuggingFaceAPIKey}
      - InputLanguage=en
    volumes:
      - ./Data:/app/Data
      - ./task_tracker.xlsx:/app/task_tracker.xlsx
      - ./config.json:/app/config.json
      - ./attendance_records.csv:/app/attendance_records.csv:rw
      - ./employees.json:/app/employees.json:rw
    restart: unless-stopped

4. Build and Run
docker build -t employee-tracker .
docker run -p 8501:8501 employee-tracker

🌐 Deploy to Render

Render supports Docker + persistent disk, which works well for your Excel/CSV-based data.

Steps

Push your project to GitHub

Create a Web Service → Docker on Render

Add environment variables:

GROQ_API_KEY

HuggingFaceAPIKey

InputLanguage=en

Add a persistent disk:

Mount path: /app/Data

Size: 1 GB

Deploy

Important

All files must be moved into the mounted disk:

/app/Data/task_tracker.xlsx
/app/Data/attendance_records.csv
/app/Data/employees.json


Update your code to read from /app/Data/...

☁️ Deploy to Streamlit Cloud

Streamlit Cloud does not support Docker or persistent files.
To make your app work, move storage to cloud services:

Use Google Sheets instead of Excel

Use gspread with a service account added in Streamlit Secrets.

Replace CSV/JSON files with

Google Sheets

MongoDB Atlas

Or Render PostgreSQL

Then push to GitHub and deploy normally on Streamlit Cloud.

💻 GitHub Codespaces (For Development)

Create .devcontainer/devcontainer.json:

{
  "name": "Employee Tracker",
  "dockerFile": "../Dockerfile",
  "forwardPorts": [8501],
  "postCreateCommand": "pip install -r requirements.txt"
}


Open Codespace → run:

streamlit run main.py


This is not for production, only development.

📊 Data Orchestration (Admin Panel + Chatbot)
Data sources

Excel: task_tracker.xlsx

CSV: attendance_records.csv

JSON: employees.json

Vector store (in memory)

Improve reliability

Refresh the chatbot index after any data update

Validate data consistency across files

Create missing data files on first startup

Add scheduled backups (local disk or S3)

🔄 Production Upgrade Path

Move from file-based storage to PostgreSQL:

employees table

attendance table

tasks table

This avoids corruption and scaling problems.

If you want, I can also create:
✅ A fully optimized folder structure
✅ A cleaned-up requirements.txt
✅ Render-ready config fixes
✅ Code changes needed for /app/Data paths
