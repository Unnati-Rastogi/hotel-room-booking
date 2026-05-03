# TVUC Hotel Booking System

A full-stack hotel booking application with a 3D building interface.

## Prerequisites
1.  **Python 3.8+** installed.
2.  **MySQL Server** installed and running.

## Setup Instructions

### 1. Install Dependencies
Open your terminal in this folder and run:
```powershell
pip install -r requirements.txt
```

### 2. Configure Database
1.  Open `app.py`, `reviews.py`, and `import_schema.py`.
2.  Locate the `DB_CONFIG` (or `HOST`/`USER`/`PASSWORD`) section near the top of each file.
3.  Ensure the `password` matches your local MySQL root password. (Default is `@R00t123` in the code).

### 3. Initialize Database Schema
Run the following command to create the database and tables:
```powershell
python import_schema.py
```

### 4. Start the Application
Run the Flask server:
```powershell
python app.py
```

### 5. Open in Browser
Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) to start booking rooms!

---

## Admin Credentials
- **Email**: `admin@tvuc.com`
- **Password**: `admin123`
