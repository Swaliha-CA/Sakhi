// Dashboard Controller
class Dashboard {
    constructor() {
        this.moduleWindows = {};
        this.init();
    }

    init() {
        // Check API status on load
        this.checkAPIStatus();
        
        // Check API status every 30 seconds
        setInterval(() => this.checkAPIStatus(), 30000);

        // Animate stats on load
        this.animateStats();
    }

    async checkAPIStatus() {
        const statusIcon = document.getElementById('apiStatusIcon');
        const statusText = document.getElementById('apiStatusText');

        try {
            const response = await fetch('http://localhost:8000/health');
            if (response.ok) {
                statusIcon.className = 'fas fa-circle text-success';
                statusText.textContent = 'API Online';
            } else {
                throw new Error('API not responding');
            }
        } catch (error) {
            statusIcon.className = 'fas fa-circle text-danger';
            statusText.textContent = 'API Offline';
        }
    }

    animateStats() {
        const statBoxes = document.querySelectorAll('.stat-box h2');
        statBoxes.forEach(stat => {
            const finalValue = stat.textContent;
            const isNumber = !isNaN(parseInt(finalValue));
            
            if (isNumber) {
                const target = parseInt(finalValue.replace(/[^0-9]/g, ''));
                this.animateValue(stat, 0, target, 2000, finalValue.includes('%'));
            }
        });
    }

    animateValue(element, start, end, duration, isPercentage) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= end) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current) + (isPercentage ? '%' : '');
        }, 16);
    }
}

// Module Router - Opens modules in separate windows
function openModule(moduleName) {
    const moduleRoutes = {
        // Live API Modules
        'ocr': 'modules/ocr.html',
        'alternatives': 'modules/alternatives.html',
        'voice': 'modules/voice.html',
        'notifications': 'modules/notifications.html',
        'exposure': 'modules/exposure.html',
        'ppd': '../demo/screens/ppd-prediction-interactive.html',
        'micronutrients': '../demo/screens/micronutrients-interactive.html',
        'asha': '../demo/screens/asha-dashboard-interactive.html',
        
        // Demo Modules
        'sutika': '../demo/screens/sutika.html',
        'offline': '../demo/screens/offline-sync.html',
        'climate': '../demo/screens/climate-shield.html',
        'buddy': '../demo/screens/buddy-system.html',
        'analytics': '../demo/screens/analytics.html',
        'predictive': '../demo/screens/implementation.html',
        'architecture': '../demo/screens/architecture.html'
    };

    const route = moduleRoutes[moduleName];
    if (!route) {
        console.error('Module not found:', moduleName);
        return;
    }

    // Window features for a nice popup
    const features = 'width=1400,height=900,left=100,top=50,resizable=yes,scrollbars=yes,status=yes';
    
    // Open in new window
    const windowName = `sakhi_${moduleName}`;
    const moduleWindow = window.open(route, windowName, features);

    if (moduleWindow) {
        moduleWindow.focus();
    } else {
        // Fallback to new tab if popup blocked
        window.open(route, '_blank');
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});

// Make openModule available globally
window.openModule = openModule;
