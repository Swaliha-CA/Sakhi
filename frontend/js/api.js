// API Client
class APIClient {
    constructor() {
        this.baseURL = API_CONFIG.BASE_URL + API_CONFIG.API_PREFIX;
        this.timeout = API_CONFIG.TIMEOUT;
    }

    async request(endpoint, options = {}) {
        const url = this.baseURL + endpoint;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    ...options.headers
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }

    async postFormData(endpoint, formData) {
        return this.request(endpoint, {
            method: 'POST',
            body: formData
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // OCR Methods
    async extractText(file, language = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (language) {
            formData.append('language', language);
        }
        return this.postFormData(API_CONFIG.ENDPOINTS.OCR_EXTRACT, formData);
    }

    async detectLanguage(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.postFormData(API_CONFIG.ENDPOINTS.OCR_DETECT_LANG, formData);
    }

    // Alternatives Methods
    async findAlternatives(data) {
        return this.post(API_CONFIG.ENDPOINTS.ALTERNATIVES_FIND, data);
    }

    async addToShoppingList(data) {
        return this.post(API_CONFIG.ENDPOINTS.ALTERNATIVES_SHOPPING_LIST, data);
    }

    async getShoppingList(userId, sortByPriority = true) {
        return this.get(`${API_CONFIG.ENDPOINTS.ALTERNATIVES_SHOPPING_LIST}/${userId}?sort_by_priority=${sortByPriority}`);
    }

    async removeFromShoppingList(userId, itemId) {
        return this.delete(`${API_CONFIG.ENDPOINTS.ALTERNATIVES_SHOPPING_LIST}/${userId}/${itemId}`);
    }

    async getNotifications(userId, unreadOnly = false, limit = 20) {
        return this.get(`${API_CONFIG.ENDPOINTS.ALTERNATIVES_NOTIFICATIONS}/${userId}?unread_only=${unreadOnly}&limit=${limit}`);
    }

    async markNotificationRead(userId, notificationId) {
        return this.post(`${API_CONFIG.ENDPOINTS.ALTERNATIVES_NOTIFICATIONS}/${userId}/${notificationId}/read`, {});
    }

    // Voice Methods
    async speechToText(audioBlob, language = null, autoDetect = true) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        if (language) {
            formData.append('language', language);
        }
        formData.append('auto_detect', autoDetect);
        return this.postFormData(API_CONFIG.ENDPOINTS.VOICE_STT, formData);
    }

    async textToSpeech(text, language, gender = 'FEMALE') {
        return this.post(API_CONFIG.ENDPOINTS.VOICE_TTS, { text, language, gender });
    }

    async startScreening(screeningType, language, userId) {
        return this.post(API_CONFIG.ENDPOINTS.VOICE_SCREENING_START, {
            screening_type: screeningType,
            language: language,
            user_id: userId
        });
    }

    async respondToScreening(sessionId, responseText, confidence) {
        return this.post(API_CONFIG.ENDPOINTS.VOICE_SCREENING_RESPOND, {
            session_id: sessionId,
            response_text: responseText,
            confidence: confidence
        });
    }

    async getSupportedLanguages() {
        return this.get(API_CONFIG.ENDPOINTS.VOICE_LANGUAGES);
    }

    // Health Check
    async checkHealth() {
        return this.get(API_CONFIG.ENDPOINTS.HEALTH);
    }
}

// Create global API client instance
window.api = new APIClient();
