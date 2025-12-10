# Analytics Crawler & Validator UI

An interactive web application for crawling websites and validating Adobe Analytics implementation with real-time status updates.

## Features

- **Interactive UI**: Modern React-based interface for easy configuration
- **Real-time Updates**: WebSocket-based live status updates during crawling and validation
- **Flexible Validator Selection**: Choose which validators to run via checkboxes
- **Expandable Results**: Click on any validator to see detailed output
- **Visual Feedback**: Spinning wheels for running tasks, success/failure icons
- **Comprehensive Validation**: Five built-in validators for Adobe Analytics

## Architecture

- **Backend**: FastAPI with WebSocket support
- **Frontend**: React with Vite
- **Crawler**: crawl4ai with mitmproxy for network capture
- **Validators**: Python scripts for Adobe Analytics validation

## Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

## Installation

### 1. Backend Setup

Install Python dependencies:

```bash
# Install crawler dependencies
pip install -r requirements.txt

# Install API server dependencies
pip install -r requirements-api.txt
```

### 2. Frontend Setup

Install Node.js dependencies:

```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend Server

From the project root:

```bash
python3 api_server.py
```

The API server will start on `http://localhost:8000`

### Start the Frontend Development Server

In a new terminal, from the `frontend` directory:

```bash
cd frontend
npm run dev
```

The React app will start on `http://localhost:3000`

## Usage

1. Open your browser to `http://localhost:3000`
2. Enter the website URL you want to scan
3. Select which validators you want to run (all selected by default)
4. Click "Start Scan"
5. Watch the real-time progress as crawling and validation occurs
6. Click on any validator to expand and see detailed results

## Available Validators

### Required Fields
Validates that all events contain required XDM fields (eventType, timestamp, identityMap)

### ECID Consistency
Validates that all requests share the same ECID (Experience Cloud ID)

### Page View Integrity
Validates exactly one page view event per page

### No Duplicate Events
Validates no duplicate events within time window (1 second)

### Payload Size
Validates payload sizes are under limit (32 KB)

## API Endpoints

### WebSocket
- `ws://localhost:8000/ws` - Real-time status updates

### REST Endpoints
- `GET /api/validators` - Get list of available validators
- `POST /api/crawl` - Start crawl and validation
- `GET /api/health` - Health check

## Project Structure

```
crawler/
├── api_server.py           # FastAPI backend server
├── crawler.py             # Core crawler logic
├── run_validators.py      # Validator orchestration
├── mitmproxy_utils.py     # Proxy utilities
├── validators/            # Validator scripts
│   ├── required_fields.py
│   ├── ecid_consistency.py
│   ├── page_view_integrity.py
│   ├── no_duplicate_events.py
│   └── payload_size.py
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── CrawlerForm.jsx
│   │   │   ├── CrawlerForm.css
│   │   │   ├── StatusDisplay.jsx
│   │   │   └── StatusDisplay.css
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── requirements.txt       # Crawler dependencies
└── requirements-api.txt   # API server dependencies
```

## Development

### Adding New Validators

1. Create a new validator script in `validators/` directory
2. Add the validator definition in `api_server.py` in the `all_validators` dictionary
3. Add the validator info in the `/api/validators` endpoint
4. The UI will automatically display the new validator as a checkbox option

### Customizing Crawl Settings

In `api_server.py`, you can modify:
- `max_pages`: Maximum pages to crawl (default: 4)
- `max_depth`: Maximum crawl depth (default: 2)
- `network_patterns`: Regex patterns for network capture

## Troubleshooting

### Backend Issues

**Import errors for fastapi/uvicorn:**
```bash
pip install -r requirements-api.txt
```

**Crawler errors:**
```bash
pip install -r requirements.txt
```

### Frontend Issues

**Module not found errors:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Port already in use:**
- Change the port in `frontend/vite.config.js`
- Update the API_URL in `frontend/src/App.jsx`

### WebSocket Connection Issues

Make sure:
1. Backend server is running on port 8000
2. Frontend is connecting to the correct WebSocket URL
3. No CORS issues (CORS is configured for localhost:3000 and localhost:5173)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
