// Utility Functions

// Show toast notification
function showToast(message, type = 'info') {
    const toastEl = document.getElementById('liveToast');
    const toastBody = toastEl.querySelector('.toast-body');
    
    // Set message
    toastBody.textContent = message;
    
    // Set color based on type
    toastEl.className = 'toast';
    if (type === 'success') {
        toastEl.classList.add('bg-success', 'text-white');
    } else if (type === 'error') {
        toastEl.classList.add('bg-danger', 'text-white');
    } else if (type === 'warning') {
        toastEl.classList.add('bg-warning');
    }
    
    // Show toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: APP_CONFIG.TOAST_DURATION
    });
    toast.show();
}

// Show/hide loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Get score color class
function getScoreClass(score) {
    if (score >= 80) return 'score-safe';
    if (score >= 50) return 'score-warning';
    return 'score-danger';
}

// Get score badge color
function getScoreBadgeClass(score) {
    if (score >= 80) return 'bg-success';
    if (score >= 50) return 'bg-warning';
    return 'bg-danger';
}

// Validate file
function validateImageFile(file) {
    if (!file) {
        throw new Error('No file selected');
    }
    
    if (!APP_CONFIG.ALLOWED_IMAGE_TYPES.includes(file.type)) {
        throw new Error('Invalid file type. Please upload a JPEG, PNG, or WebP image.');
    }
    
    if (file.size > APP_CONFIG.MAX_FILE_SIZE) {
        throw new Error('File too large. Maximum size is 5MB.');
    }
    
    return true;
}

// Format price range
function formatPriceRange(priceRange) {
    if (!priceRange) return 'N/A';
    return `₹${priceRange}`;
}

// Truncate text
function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Check API status
async function checkAPIStatus() {
    try {
        await api.checkHealth();
        updateAPIStatus(true);
    } catch (error) {
        updateAPIStatus(false);
    }
}

function updateAPIStatus(isOnline) {
    const statusIcon = document.getElementById('apiStatus');
    const statusText = document.getElementById('apiStatusText');
    
    if (isOnline) {
        statusIcon.className = 'fas fa-circle text-success';
        statusText.textContent = 'Online';
    } else {
        statusIcon.className = 'fas fa-circle text-danger';
        statusText.textContent = 'Offline';
    }
}

// Initialize API status check
setInterval(checkAPIStatus, 30000); // Check every 30 seconds
checkAPIStatus(); // Initial check

// Export utilities
window.utils = {
    showToast,
    showLoading,
    hideLoading,
    formatDate,
    getScoreClass,
    getScoreBadgeClass,
    validateImageFile,
    formatPriceRange,
    truncateText,
    debounce,
    checkAPIStatus,
    updateAPIStatus
};
