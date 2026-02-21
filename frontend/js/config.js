// API Configuration
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    API_PREFIX: '/api/v1',
    TIMEOUT: 30000, // 30 seconds
    
    // Endpoints
    ENDPOINTS: {
        // OCR
        OCR_EXTRACT: '/ocr/extract-text',
        OCR_DETECT_LANG: '/ocr/detect-language',
        OCR_HEALTH: '/ocr/health',
        
        // Alternatives
        ALTERNATIVES_FIND: '/alternatives/find',
        ALTERNATIVES_SHOPPING_LIST: '/alternatives/shopping-list',
        ALTERNATIVES_NOTIFICATIONS: '/alternatives/notifications',
        
        // Voice
        VOICE_STT: '/voice/stt',
        VOICE_TTS: '/voice/tts',
        VOICE_SCREENING_START: '/voice/screening/start',
        VOICE_SCREENING_RESPOND: '/voice/screening/respond',
        VOICE_LANGUAGES: '/voice/languages',
        
        // Buddy System
        BUDDY_LINK: '/buddy/link',
        BUDDY_RECIPES: '/buddy/recipes',
        
        // Notifications
        NOTIFICATIONS_GET: '/notifications',
        NOTIFICATIONS_MARK_READ: '/notifications/mark-read',
        
        // Population Health
        POPULATION_HEALTH: '/population-health/dashboard',
        
        // Health Check
        HEALTH: '/health'
    }
};

// App Configuration
const APP_CONFIG = {
    USER_ID: 1, // Default user ID for demo
    DEVICE_ID: 'web-app-' + Date.now(),
    MAX_FILE_SIZE: 5 * 1024 * 1024, // 5MB
    ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/webp'],
    TOAST_DURATION: 3000
};

// Export for use in other files
window.API_CONFIG = API_CONFIG;
window.APP_CONFIG = APP_CONFIG;
