# TVUC Smart Hotel Booking System

A premium, full-stack hotel reservation platform featuring an interactive 3D building visualizer, real-time availability tracking, and a secure administration panel.

## Key Features
- **3D Interactive Building**: Browse rooms by rotating a 3D model of the hotel.
- **Smart Filtering**: Filter rooms by Floor, View (Sea, Pool, Garden, City), Type (Suite, Double, Single), and Price.
- **Secure Booking**: Automated guest record management and payment simulation (Full, Advance, or Cash).
- **Admin Dashboard**: Full control over reservations, bulk room release, and session security.
- **Breakfast Service**: Optional breakfast tracking with automated fee calculation.
- **Auto-Release**: Background scheduler automatically frees rooms once the check-out date passes.
- **Guest Reviews**: Room-specific feedback system with context-aware auto-fill.

---

## Technology Stack
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (No frameworks).
- **Backend**: Python 3.13+ with Flask.
- **Database**: MySQL with triggers for status management.

---

## Setup Instructions

### 1. Prerequisites
- **Python 3.8+**
- **MySQL Server** installed and running.

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Database Configuration
1. Open `app.py`.
2. Update the `DB_CONFIG` section (lines 23-30) with your MySQL credentials:
   ```python
   DB_CONFIG = {
       "host":     "localhost",
       "user":     "root",
       "password": "YOUR_PASSWORD_HERE",
       "database": "hotel_booking",
   }
   ```
3. Ensure you have a database named `hotel_booking` or let the app create it.

### 4. Start the Application
Run the Flask server:
```powershell
python app.py
```
*Note: The app will automatically verify tables and columns on startup.*

### 5. Open in Browser
Visit [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Admin Credentials
- **Email**: `admin@tvuc.com`
- **Password**: `admin123`

---

## Academic Summary (For Evaluators)
The system demonstrates advanced concepts including:
1. **Relational Data Integrity**: Foreign keys between `bookings`, `payments`, and `rooms`.
2. **Database Triggers**: `trg_after_booking_insert` handles automatic state transitions.
3. **Multi-threaded Backend**: A daemon thread in Flask manages the auto-checkout logic.
4. **CSS 3D Transforms**: Advanced UI rendering without external libraries like Three.js.
