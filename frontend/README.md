# DHI Transaction Analytics Dashboard

A modern, responsive web application for transaction analytics with media capture capabilities. Built with FastAPI backend and vanilla JavaScript frontend, optimized for both desktop and mobile devices.

## Features

### 📊 Analytics Dashboard
- **Real-time Transaction Visualization**: Interactive charts and graphs
- **Category-based Analysis**: Spending breakdown by categories
- **Merchant Analytics**: Top merchants and spending patterns
- **Anomaly Detection**: Automatically detect unusual transactions
- **Monthly Trends**: Historical spending analysis

### 📱 Mobile-First Design
- **Responsive Layout**: Optimized for all screen sizes
- **Touch Interface**: Touch-friendly controls and navigation
- **PWA Support**: Install as native app on mobile devices
- **Offline Mode**: Works without internet connection
- **Fast Loading**: Optimized for mobile networks

### 📷 Media Capture
- **Camera Integration**: Take photos directly in the app
- **Front/Back Camera**: Switch between cameras on mobile
- **Photo Gallery**: View and manage captured photos
- **High Quality**: Support for HD photo capture

### 🎙️ Audio Recording
- **Voice Notes**: Record audio directly in the browser
- **Playback Controls**: Play, pause, and manage recordings
- **Audio Storage**: Save recordings locally
- **Multiple Formats**: Support for various audio formats

### 📤 File Management
- **Drag & Drop Upload**: Easy file uploading
- **Multiple File Types**: Support for images, audio, documents
- **Progress Tracking**: Real-time upload progress
- **File Browser**: Manage uploaded files

### 🔧 API Monitoring
- **Service Status**: Real-time API health monitoring
- **System Logs**: View system events and errors
- **Performance Metrics**: API response times
- **Auto-refresh**: Automatic status updates

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js (optional, for development)
- Docker (for services)

### Installation

1. **Start the Frontend Server:**
   ```bash
   cd /home/hardik/dhi.core
   ./scripts/start_frontend.sh
   ```

2. **Access the Dashboard:**
   - Open: http://localhost:8081
   - Mobile: Same URL works on mobile devices

3. **Install as PWA (Optional):**
   - Desktop: Look for install prompt in browser
   - Mobile: Add to home screen from browser menu

### Manual Setup

1. **Install Dependencies:**
   ```bash
   pip install fastapi uvicorn aiofiles python-multipart
   ```

2. **Start Backend:**
   ```bash
   cd frontend
   python frontend_server.py
   ```

3. **Access Dashboard:**
   ```
   http://localhost:8081
   ```

## Usage Guide

### Dashboard Navigation

The dashboard uses a sidebar navigation with the following sections:

- **📊 Dashboard**: Main analytics overview
- **📈 Analytics**: Advanced data analysis
- **🔧 API Status**: Service monitoring
- **📷 Media Capture**: Camera functionality
- **📤 File Upload**: File management
- **🎙️ Audio Recording**: Voice recording
- **💳 Transactions**: Transaction details
- **⚙️ Settings**: App configuration

### Mobile Usage

#### Camera Capture
1. Navigate to "Media Capture"
2. Tap "Start Camera"
3. Use "Switch Camera" to toggle front/back
4. Tap "Take Photo" to capture
5. Photos appear in the gallery

#### Audio Recording
1. Navigate to "Audio Recording"
2. Tap the red record button
3. Speak into microphone
4. Tap stop to finish
5. Use playback controls to review

#### File Upload
1. Navigate to "File Upload"
2. Tap "Select Files" or drag files onto the area
3. Multiple files can be selected
4. Progress bar shows upload status

### Desktop Features

#### Advanced Analytics
- Click different chart types in Analytics section
- Hover over charts for detailed information
- Use time range filters
- Export data as JSON/CSV

#### API Monitoring
- Real-time status indicators
- System logs with timestamps
- Manual refresh capabilities
- Service health checks

## Architecture

### Frontend Stack
- **HTML5**: Semantic markup with accessibility
- **CSS3**: Modern styling with CSS Grid/Flexbox
- **JavaScript (ES6+)**: Vanilla JS with modern features
- **Bootstrap 5**: Responsive framework
- **Chart.js**: Data visualization
- **Font Awesome**: Icons

### Backend Stack
- **FastAPI**: High-performance web framework
- **Uvicorn**: ASGI server
- **aiofiles**: Async file operations
- **Python 3.8+**: Core language

### PWA Features
- **Service Worker**: Offline caching and background sync
- **Web App Manifest**: Native app installation
- **Responsive Design**: Mobile-optimized layout
- **Push Notifications**: Real-time alerts

## API Endpoints

### Frontend API
```
GET  /                          # Dashboard HTML
GET  /api/health               # Health check
GET  /api/status/all           # Service statuses
GET  /api/logs                 # System logs
POST /api/upload               # File upload
POST /api/media/photo          # Photo upload
POST /api/media/audio          # Audio upload
GET  /api/analytics/dashboard  # Analytics data
GET  /api/settings             # App settings
POST /api/settings             # Save settings
```

### Proxy Endpoints
```
GET /api/plaid/proxy/*         # Proxy to Plaid API
```

## Configuration

### Environment Variables
```bash
HOST=0.0.0.0                   # Server host
PORT=8081                      # Server port
PLAID_API_URL=http://localhost:8080  # Plaid API endpoint
NEO4J_URL=bolt://localhost:7687      # Neo4j database
```

### Settings File
Settings are stored in `frontend/settings.json`:
```json
{
  "plaid_api_url": "http://localhost:8080",
  "neo4j_url": "bolt://localhost:7687",
  "refresh_interval": 30,
  "theme": "light",
  "enable_notifications": true,
  "auto_refresh": true
}
```

## Development

### File Structure
```
frontend/
├── index.html              # Main dashboard HTML
├── dashboard.js             # Frontend JavaScript
├── frontend_server.py      # Backend API server
├── manifest.json            # PWA manifest
├── sw.js                   # Service worker
├── uploads/                # Uploaded files
├── media/                  # Captured photos
├── audio/                  # Audio recordings
└── static/                 # Static assets
```

### Local Development

1. **Enable Debug Mode:**
   ```bash
   export DEBUG=1
   python frontend_server.py
   ```

2. **Watch for Changes:**
   The server automatically reloads on code changes.

3. **Browser DevTools:**
   - Use Console for debugging
   - Network tab for API calls
   - Application tab for PWA features

### Adding Features

#### New API Endpoint
```python
@app.get("/api/new-feature")
async def new_feature():
    return {"data": "feature_data"}
```

#### New Dashboard Section
1. Add HTML section to `index.html`
2. Add navigation button
3. Add JavaScript handler
4. Update CSS styling

## Security

### Content Security Policy
The app implements CSP headers for security:
- Scripts: Self and trusted CDNs only
- Images: Self and data URLs
- Connections: Specified API endpoints only

### File Upload Security
- File type validation
- Size limits enforced
- Secure filename generation
- Virus scanning (recommended for production)

### API Security
- CORS properly configured
- Request rate limiting
- Input validation
- Error handling

## Performance

### Optimization Features
- **Lazy Loading**: Charts and media load on demand
- **Caching**: Service worker caches resources
- **Compression**: Gzip compression enabled
- **Minification**: Assets are minified in production

### Mobile Optimization
- **Touch Targets**: Minimum 44px touch targets
- **Viewport**: Proper viewport meta tag
- **Image Optimization**: Responsive images
- **Network Efficiency**: Minimal data usage

## Troubleshooting

### Common Issues

#### Frontend Won't Start
```bash
# Check dependencies
pip install -r requirements.txt

# Check port availability
lsof -i :8081

# Start with debug
DEBUG=1 python frontend_server.py
```

#### Camera Not Working
- Check browser permissions
- Ensure HTTPS (required for camera on some browsers)
- Try different browsers
- Check if other apps are using camera

#### Audio Recording Issues
- Check microphone permissions
- Ensure browser supports MediaRecorder API
- Try different browsers
- Check audio input device

#### File Upload Fails
- Check file size limits
- Verify file types are supported
- Check available disk space
- Review server logs

### Browser Compatibility

#### Supported Browsers
- **Chrome 80+**: Full feature support
- **Firefox 75+**: Full feature support
- **Safari 13+**: Full feature support
- **Edge 80+**: Full feature support

#### Required Features
- ES6+ JavaScript support
- WebRTC for camera/audio
- File API for uploads
- Service Workers for PWA

### Mobile Compatibility

#### iOS
- Safari 13+ required
- Camera requires user gesture
- PWA installation via Share menu

#### Android
- Chrome 80+ recommended
- Camera permissions required
- PWA installation via browser prompt

## Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim
COPY frontend/ /app/
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "frontend_server:app", "--host", "0.0.0.0", "--port", "8081"]
```

### Environment Setup
```bash
# Production environment variables
export HOST=0.0.0.0
export PORT=8081
export DEBUG=0
export PLAID_API_URL=https://api.example.com
```

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name dashboard.example.com;
    
    location / {
        proxy_pass http://localhost:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### HTTPS Setup
```bash
# Using Let's Encrypt
certbot --nginx -d dashboard.example.com
```

## Contributing

### Code Style
- Use ESLint for JavaScript
- Follow PEP 8 for Python
- Use meaningful variable names
- Add comments for complex logic

### Testing
```bash
# Run frontend tests
python scripts/demo_frontend.py

# Manual testing checklist
# - All navigation works
# - Camera captures photos
# - Audio records properly
# - Files upload successfully
# - Charts display data
# - Mobile responsive works
```

## License

This project is part of the DHI.core system. See the main project LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review system logs at `/api/logs`
3. Use browser developer tools
4. Check the main DHI.core documentation

---

**Made with ❤️ for DHI Transaction Analytics**
