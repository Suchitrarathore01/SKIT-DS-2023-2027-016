# ChainShield Frontend

This directory contains the user-facing interfaces for **ChainShield**, a blockchain-backed phishing and smishing threat detection system.

## Sub-projects

1. **`dashboard/`** — A modern, responsive React web dashboard built with Vite.
2. **`extension/`** — A lightweight Manifest V3 Chrome Extension popup.
3. **`shared/`** — Shared API client definitions and utilities.

---

## 0. Running the Backend First

Both the React Dashboard and the Chrome Extension communicate with the FastAPI backend.

> **Important:** The backend must be running for live scans and history retrieval to work.

### Backend Startup Commands
From the project root (`~/Projects/SKIT-DS-2023-2027-016`):
```bash
# 1. Activate your virtual environment
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# 2. Ensure dependencies from requirements.txt are installed
pip install -r requirements.txt

# 3. Start the FastAPI server on port 8000
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Once started, verify that the backend is responding:
```bash
curl http://127.0.0.1:8000/
# Expected response: {"message":"ChainShield Backend is Running!"}
```

---

## 1. Web Dashboard (`dashboard/`)

### Architecture & Theme
- **Framework**: React 18 + React Router v6.
- **Bundler**: Vite 5.
- **Theme**: Light cybersecurity aesthetic — clean white background (`#ffffff`), deep navy headings/sidebar (`#0d2340`), restrained teal primary accents (`#0e7490`), subtle borders (`#dde3ec`), and accessible contrast.
- **Data Integrity**: Real backend responses only. Never fabricates ML confidence scores, threat statistics, or false safety guarantees.

### Pages & Features
- **Overview**: System explanation, workflow overview, and core detection capabilities.
- **URL Scanner**: Live URL input form hooked directly to `POST /scan` sending `{"url":"https://..."}`. Displays risk badges (`SAFE`, `MEDIUM`, `HIGH`, `UNKNOWN`), domain and protocol parsing, HTTPS & IP indicators, plain text security findings, and real-time Ethereum Sepolia blockchain registry lookup status.
- **Scan History**: Live history table connected to `GET /scan/history` with collapsible inspection cards, auto-refresh, empty states, and loading skeletons. Does not display blockchain status on history items because those are not stored in the database.

### Setup & Development
```bash
cd frontend/dashboard

# Install dependencies
npm install

# Copy environment example
cp .env.example .env

# Run development server (defaults to http://localhost:5173)
npm run dev

# Build for production
npm run build
```

### Environment Configuration & Proxy
The dashboard reads the backend URL from `VITE_API_BASE_URL`:
- Default: `http://127.0.0.1:8000`
- Configured in `.env` (which is git-ignored). See `.env.example`.
- During development, `vite.config.js` also configures a reverse proxy forwarding `/scan` to `http://127.0.0.1:8000`.

---

## 2. Chrome Extension (`extension/`)

### Architecture & Permissions
- **Manifest**: Manifest V3 (`manifest.json`).
- **Design**: Clean popup interface consistent with the dashboard design system.
- **Minimal Permissions**: No broad URL matching (`<all_urls>`) and no tab-reading permissions (`tabs`, `activeTab`).
- **Host Permissions**: Requests access solely to `http://127.0.0.1:8000/*` for local backend communication.
- **Deployment Note**: When deploying the backend to a remote server or domain (e.g. `https://api.chainshield.example.com`), update `BACKEND_URL` in `src/popup.js` and update `host_permissions` in `manifest.json` to match the production domain.

### Loading into Google Chrome
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Toggle **Developer mode** in the top right corner.
3. Click **Load unpacked**.
4. Select the `frontend/extension` directory.
5. The **ChainShield** icon will appear in your extensions toolbar. Click it to open the popup.

### Generating / Updating Icons
Placeholders are pre-generated via a Node script:
```bash
cd frontend/extension
node scripts/generate-icons.js
```
To supply custom branded icons, place 16×16, 48×48, and 128×128 PNG files in `frontend/extension/icons/`.

---

## 3. Shared API Client (`shared/`)

- `frontend/shared/api.js` is the single source of truth for all API communication.
- Exports `scanUrl(url, baseUrl)` and `getScanHistory(baseUrl)`.
- Handles structured error mapping: network disconnects (`type: "network"`), HTTP errors (`type: "http"`), and malformed response bodies (`type: "parse"`).
- Dashboard components import from `src/api.js` which resolves the environment-configured base URL and delegates to `frontend/shared/api.js`.
