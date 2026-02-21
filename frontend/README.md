# SAKHI Frontend Application

Production-ready frontend application that connects to the SAKHI backend APIs.

## Features

### 1. OCR Product Scanner
- Upload product images via drag-and-drop or file selection
- Multi-language OCR support (English, Hindi, Tamil, Telugu, Bengali)
- Real-time toxicity scoring
- Confidence level display
- Direct integration with backend OCR API

### 2. Safer Product Alternatives
- Search for toxin-free alternatives by category
- Filter by price preference and region
- Shopping list management
- Add/remove items from shopping list
- Export shopping list
- Real-time API integration

### 3. Voice AI Health Screening
- Voice-based EPDS and PHQ-9 screenings
- Multi-language support (6 Indic languages)
- Real-time speech-to-text conversion
- Progress tracking
- Risk assessment with recommendations
- Microphone recording with visual feedback

### 4. Notifications
- View all notifications
- Filter unread notifications
- Mark notifications as read
- Product updates and health alerts
- Real-time notification display

## Setup

### Prerequisites
- Backend API running on `http://localhost:8000`
- Modern web browser with JavaScript enabled
- Microphone access for voice features

### Installation

1. **Start the Backend Server**
   ```bash
   cd tinkher
   python -m uvicorn app.main:app --reload
   ```

2. **Serve the Frontend**
   
   Option A: Using Python's built-in server
   ```bash
   cd frontend
   python -m http.server 8080
   ```

   Option B: Using Node.js http-server
   ```bash
   cd frontend
   npx http-server -p 8080
   ```

   Option C: Using VS Code Live Server extension
   - Open `frontend/index.html` in VS Code
   - Right-click and select "Open with Live Server"

3. **Access the Application**
   - Open browser and navigate to `http://localhost:8080`
   - Ensure backend is running at `http://localhost:8000`

## Configuration

Edit `js/config.js` to change API settings:

```javascript
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',  // Change to your backend URL
    API_PREFIX: '/api/v1',
    TIMEOUT: 30000
};
```

## Project Structure

```
frontend/
├── index.html              # Main HTML file
├── css/
│   └── main.css           # Styles
├── js/
│   ├── config.js          # Configuration
│   ├── api.js             # API client
│   ├── utils.js           # Utility functions
│   ├── app.js             # Main application
│   └── components/
│       ├── home.js        # Home page
│       ├── ocr.js         # OCR scanner
│       ├── alternatives.js # Product alternatives
│       ├── voice.js       # Voice AI
│       └── notifications.js # Notifications
└── README.md              # This file
```

## API Integration

### OCR Scanner
- `POST /api/v1/ocr/extract-text` - Extract text from image
- `POST /api/v1/ocr/detect-language` - Detect language from image

### Alternatives
- `POST /api/v1/alternatives/find` - Find safer alternatives
- `POST /api/v1/alternatives/shopping-list` - Add to shopping list
- `GET /api/v1/alternatives/shopping-list/{user_id}` - Get shopping list
- `DELETE /api/v1/alternatives/shopping-list/{user_id}/{item_id}` - Remove from list

### Voice AI
- `POST /api/v1/voice/stt` - Speech to text
- `POST /api/v1/voice/tts` - Text to speech
- `POST /api/v1/voice/screening/start` - Start screening
- `POST /api/v1/voice/screening/respond` - Respond to question

### Notifications
- `GET /api/v1/alternatives/notifications/{user_id}` - Get notifications
- `POST /api/v1/alternatives/notifications/{user_id}/{notification_id}/read` - Mark as read

## Features

### Real-time API Integration
- All features connect to actual backend APIs
- No mock data or simulations
- Real-time data processing

### Error Handling
- Comprehensive error messages
- Toast notifications for user feedback
- Loading indicators during API calls
- API status monitoring

### Responsive Design
- Mobile-friendly interface
- Bootstrap 5 framework
- Modern, clean UI
- Smooth animations and transitions

### User Experience
- Drag-and-drop file upload
- Real-time progress tracking
- Visual feedback for all actions
- Intuitive navigation

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### API Connection Issues
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in backend
3. Verify API_CONFIG.BASE_URL in config.js

### Microphone Not Working
1. Grant microphone permissions in browser
2. Use HTTPS or localhost (required for getUserMedia)
3. Check browser console for errors

### File Upload Issues
1. Check file size (max 5MB)
2. Verify file type (JPG, PNG, WebP only)
3. Check backend file upload limits

## Development

### Adding New Features
1. Create component file in `js/components/`
2. Add component to `app.js` components object
3. Add navigation link in `index.html`
4. Implement render() and init() methods

### Styling
- Edit `css/main.css` for global styles
- Use Bootstrap 5 utility classes
- Follow existing color scheme (CSS variables)

## Production Deployment

### Build Steps
1. Minify JavaScript files
2. Optimize images
3. Enable caching headers
4. Use CDN for libraries
5. Configure production API URL

### Security
- Use HTTPS in production
- Implement authentication
- Validate all user inputs
- Sanitize API responses

## License

Part of the SAKHI Women's Health Platform project.

## Support

For issues or questions, please refer to the main project repository.
