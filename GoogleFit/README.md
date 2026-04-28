# 🏥 Health Dashboard

**Real-time health data visualization from Google Fit and Strava**

A modern, beautiful desktop dashboard that displays your actual fitness data with smooth animations and a clean dark theme.

![React](https://img.shields.io/badge/React-18.2-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![Tailwind](https://img.shields.io/badge/Tailwind-3.3-cyan)

---

## 🚀 Quick Start

### One-Click Setup

**Just double-click:** `RUN-DASHBOARD.bat`

That's it! The script will:
- ✅ Install all dependencies automatically
- ✅ Open browser for Google authorization
- ✅ Start Flask API server (Port 5000)
- ✅ Start React frontend (Port 3000)
- ✅ Open dashboard automatically

---

## 📋 Prerequisites

Before running, make sure you have:

1. **Python 3.8+** → [Download](https://www.python.org/downloads/)
2. **Node.js 16+** → [Download](https://nodejs.org/)
3. **Google Fit Credentials** (see setup below)

---

## 🔐 Google Fit Setup (First Time Only)

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Create Project" (or select existing)
3. Enter project name → Click "Create"

### Step 2: Enable Fitness API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Fitness API"
3. Click "Enable"

### Step 3: Create Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: **External**
   - App name: Your choice
   - Support email: Your email
   - Click "Save and Continue"
4. Application type: **Desktop app**
5. Name: Any name (e.g., "Health Dashboard")
6. Click "Create"
7. Download JSON file
8. **Rename to `credentials.json`**
9. **Place in `GoogleFit/` folder** (same directory as RUN-DASHBOARD.bat)

### Step 4: Run Dashboard

Double-click `RUN-DASHBOARD.bat` → Browser opens → Grant permissions → Done!

---

## 🎯 Optional: Strava Setup

Want Strava data too? Follow these steps:

1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Create application
3. Note your Client ID and Client Secret
4. Create `.env` file in `GoogleFit/` folder:
   ```env
   STRAVA_CLIENT_ID=your_client_id_here
   STRAVA_CLIENT_SECRET=your_client_secret_here
   ```
5. Run: `python strava_fetcher.py` → Authorize in browser
6. Restart dashboard

---

## 📁 Project Structure

```
GoogleFit/
├── RUN-DASHBOARD.bat          ← START HERE (One-click startup)
│
├── Backend (Python/Flask)
│   ├── api_server.py          ← Flask API server
│   ├── google_fit_api.py      ← Google Fit integration
│   ├── strava_fetcher.py      ← Strava integration
│   ├── auth.py                ← Authentication logic
│   ├── time_utils.py          ← Date utilities
│   ├── normalizer.py          ← Data normalization
│   └── requirements.txt       ← Python dependencies
│
├── Frontend (React)
│   └── dashboard-ui/          ← Complete React application
│       ├── src/
│       │   ├── components/    ← React components
│       │   ├── utils/         ← API client, date helpers
│       │   └── ...
│       ├── package.json
│       ├── vite.config.js
│       └── tailwind.config.js
│
├── Configuration
│   ├── credentials.json       ← YOUR Google credentials
│   ├── token.json             ← Auto-generated auth tokens
│   └── .env                   ← Strava credentials (optional)
│
└── README.md                  ← This file
```

---

## ✨ Features

### Dashboard Capabilities
- 🔄 **Real-time data** from Google Fit and Strava APIs
- 🎨 **Beautiful UI** with modern skeuomorphic dark theme
- ✨ **Smooth animations** using Framer Motion
- 📅 **Date range selection** (Today, Last 7/30 Days, This Week/Month)
- 🔀 **Source switcher** between Google Fit and Strava
- 🎯 **Independent state** - no data interference between sources
- ⚡ **Fast loading** with loading states and error handling

### Google Fit Metrics
- **Steps** - Daily step count with progress
- **Active Minutes** - Time spent moving
- **Calories** - Energy burned
- **Distance** - Total distance covered
- **Sleep** - Sleep duration tracking
- **Activity Segments** - Detailed breakdown

### Strava Metrics
- **Activities** - Total workout count
- **Distance** - Kilometers/miles covered
- **Duration** - Time spent exercising
- **Calories** - Energy expended
- **Recent Activities** - List of latest workouts

### Date Range Options
- **Today** (default - calendar day 00:00 to 23:59)
- **Yesterday**
- **Last 7 Days**
- **Last 30 Days**
- **This Week**
- **This Month**

---

## 🔧 Manual Setup (Alternative)

If you prefer manual control:

### Terminal 1 - Backend
```bash
cd c:\Users\harsh\OneDrive\Desktop\GoogleFit
pip install -r requirements.txt
python api_server.py
```

### Terminal 2 - Frontend
```bash
cd c:\Users\harsh\OneDrive\Desktop\GoogleFit\dashboard-ui
npm install
npm run dev
```

Then open: **http://localhost:3000**

---

## 📊 How It Works

```
┌─────────────────────┐
│  React Frontend     │  Port 3000
│  (Vite dev server)  │  • Dashboard UI
│                     │  • Framer Motion animations
└──────────┬──────────┘  • Tailwind CSS styling
           │
           │ HTTP REST API
           ▼
┌─────────────────────┐
│  Flask API Server   │  Port 5000
│  (api_server.py)    │  • GET /api/google-fit
│                     │  • GET /api/strava
└──────────┬──────────┘  • Date range handling
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐  ┌─────────┐
│ Google   │  │ Strava  │  External APIs
│ Fit API  │  │   API   │  • Real health data
└──────────┘  └─────────┘  • OAuth 2.0 auth
```

---

## 🐛 Troubleshooting

### "credentials.json not found"
**Solution:** Download from Google Cloud Console and place in `GoogleFit/` folder

### "Python is not recognized"
**Solution:** Install Python from python.org and check "Add Python to PATH" during installation

### "npm is not recognized"
**Solution:** Install Node.js from nodejs.org

### Dashboard shows "Loading..." forever
**Solutions:**
- Check Flask API is running in Terminal 1
- Test API health: http://localhost:5000/api/health
- Look for error messages in Flask terminal
- Restart both servers

### "Port 5000 already in use"
**Solutions:**
```bash
# Find the process
netstat -ano | findstr :5000

# Kill it (replace <PID> with actual process ID)
taskkill /F /PID <PID>

# Or change port in api_server.py (line 378)
```

### No Google Fit data showing
**Solutions:**
- Check that Fitness API is enabled in Google Cloud Console
- Run: `python google_fit_api.py` to re-authorize
- Grant all requested permissions in browser
- Verify `token.json` was created in project folder

### Strava not working
**Solutions:**
- Verify `.env` file exists with correct credentials
- Run: `python strava_fetcher.py` to authorize
- Check authorization was successful in browser

### API returns errors
**Solutions:**
- Check internet connection
- Verify API credentials are valid
- Check quota limits in Google Cloud Console
- Review Flask terminal for detailed error messages

---

## 💡 Tips & Best Practices

### First Run
- Takes 2-3 minutes (installing dependencies)
- Browser opens for Google authorization automatically
- Two terminal windows will open (Flask + React)
- Dashboard opens at http://localhost:3000

### Subsequent Runs
- Starts in ~10 seconds
- No authorization needed (token.json persists)
- Automatic token refresh

### Development
- Edit React files → Changes appear instantly (hot reload)
- Edit Python files → Restart Flask server (Ctrl+C, then restart)
- All Tailwind CSS classes available
- Framer Motion for smooth animations

### Stopping the Dashboard
- Press `Ctrl+C` in both terminal windows
- Or close both terminal windows

### Data Refresh
- Data updates when you change date ranges
- Switch between sources to see different metrics
- token.json refreshes automatically (no manual action needed)

---

## 🎯 Tech Stack

### Backend
- **Python 3.8+**
- **Flask 3.0+** - REST API server
- **Google Fit API** - Health data from Google
- **Strava API v3** - Activity data from Strava
- **Flask-CORS** - Cross-origin requests

### Frontend
- **React 18** - UI framework
- **Vite 5** - Build tool (fast HMR)
- **Tailwind CSS 3.3** - Utility-first styling
- **Framer Motion 10.16** - Smooth animations
- **Lucide React** - Beautiful icons

---

## ⚠️ Security & Privacy

### Your Data is Safe
- ✅ All data stays on **your computer**
- ✅ No third-party data sharing
- ✅ OAuth 2.0 secure authentication
- ✅ Automatic token refresh
- ✅ Credentials stored locally only

### NEVER Share or Commit
- ❌ `credentials.json` - YOUR Google credentials
- ❌ `token.json` - YOUR access tokens
- ❌ `.env` - YOUR Strava credentials

**These files contain your personal authentication credentials!**

---

## 📖 API Endpoints

### Health Check
```
GET /api/health
```
Returns server status

### Google Fit Data
```
GET /api/google-fit?range_type={preset}
```
Parameters:
- `range_type`: today | yesterday | last_7_days | last_30_days | this_week | this_month

Returns:
```json
{
  "steps": 8234,
  "calories": 2100,
  "active_minutes": 45,
  "distance": 6.2,
  "sleep": 7.5,
  "activity_segments": [...]
}
```

### Strava Data
```
GET /api/strava?range_type={preset}
```
Parameters: Same as Google Fit

Returns:
```json
{
  "activities_count": 5,
  "total_distance": 42.5,
  "total_duration": 180,
  "total_calories": 1200,
  "recent_activities": [...]
}
```

---

## 🧪 Testing

### Test Backend
```bash
# Start Flask server
python api_server.py

# In another terminal, test endpoints
curl http://localhost:5000/api/health
curl http://localhost:5000/api/google-fit?range_type=today
```

### Test Frontend
```bash
# Start React dev server
cd dashboard-ui
npm run dev

# Open browser to http://localhost:3000
# Open DevTools (F12) → Check for console errors
```

---

## 📦 Dependencies

### Python (requirements.txt)
```
flask>=3.0.0
flask-cors>=4.0.0
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=0.5.0
requests>=2.28.0
python-dotenv>=0.19.0
```

### JavaScript (package.json)
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "framer-motion": "^10.16.0",
  "lucide-react": "^0.294.0"
}
```

---

## 🔄 Updating

### Update Python Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Update React Dependencies
```bash
cd dashboard-ui
npm update
```

---

## ✅ Verification Checklist

### Before First Run
- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] credentials.json in GoogleFit/ folder
- [ ] Fitness API enabled in Google Cloud Console

### After Running RUN-DASHBOARD.bat
- [ ] No errors in Flask terminal
- [ ] No errors in React terminal
- [ ] Browser opens automatically
- [ ] Dashboard loads at http://localhost:3000
- [ ] Can see Google Fit metrics
- [ ] Can change date ranges
- [ ] Can switch between sources

### Testing Dashboard Features
- [ ] Today's step count shows real data
- [ ] Calories match Google Fit app
- [ ] Active minutes are accurate
- [ ] Date range picker works correctly
- [ ] Switching sources updates UI smoothly
- [ ] Animations are smooth (no lag)
- [ ] No console errors in browser (F12)

---

## 🎓 Learning Resources

### Google Fit API
- [Official Documentation](https://developers.google.com/fit)
- [REST API Reference](https://developers.google.com/fit/rest)
- [Python Client Library](https://github.com/googleapis/google-api-python-client)

### Strava API
- [Getting Started](https://developers.strava.com/docs/getting-started/)
- [API Reference](https://developers.strava.com/docs/reference/)

### React & Tailwind
- [React Documentation](https://react.dev/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Framer Motion](https://www.framer.com/motion/)

---

## 🤝 Contributing

This is a personal health dashboard project. Feel free to:
- Fork for your own use
- Customize the UI
- Add new metrics
- Integrate other health APIs

---

## 📝 License

Personal use only. Your health data remains private on your machine.

---

## 🎉 Ready to Go!

**Just double-click `RUN-DASHBOARD.bat` and enjoy tracking your health data beautifully!** 💪🏃‍♂️🚴‍♀️

---

## 📞 Quick Reference

| What | Where | Port |
|------|-------|------|
| Dashboard UI | http://localhost:3000 | 3000 |
| API Health Check | http://localhost:5000/api/health | 5000 |
| Google Fit Data | http://localhost:5000/api/google-fit | 5000 |
| Strava Data | http://localhost:5000/api/strava | 5000 |

**Start Script:** `RUN-DASHBOARD.bat`  
**Stop:** `Ctrl+C` in both terminals

---

**Version:** 1.0  
**Last Updated:** 2026-04-06
