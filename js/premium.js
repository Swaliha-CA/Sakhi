/**
 * SAKHI Premium Dashboard - Interactive Features
 */

// Smooth scroll to modules section
function scrollToModules() {
    const modulesSection = document.getElementById('modules');
    modulesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Open module in new window
function openModule(moduleName) {
    const moduleUrls = {
        'ocr': 'modules/ocr.html',
        'alternatives': 'modules/alternatives.html',
        'voice': 'modules/voice.html',
        'exposure': 'modules/exposure.html',
        'notifications': 'modules/notifications.html',
        'asha': 'http://localhost:8000/docs#/ASHA%20Dashboard',
        'ppd': 'http://localhost:8000/docs#/PPD%20Prediction'
    };
    
    const url = moduleUrls[moduleName];
    if (url) {
        window.open(url, '_blank', 'width=1200,height=800');
    }
}

// Intersection Observer for fade-in animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe all module cards
document.addEventListener('DOMContentLoaded', () => {
    const moduleCards = document.querySelectorAll('.module-card-premium');
    moduleCards.forEach(card => observer.observe(card));
    
    // Add stagger animation delay
    moduleCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
    });
});

// Navbar scroll effect
let lastScroll = 0;
const navbar = document.querySelector('.navbar-premium');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 100) {
        navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.08)';
        navbar.style.background = 'rgba(255, 255, 255, 0.95)';
    } else {
        navbar.style.boxShadow = 'none';
        navbar.style.background = 'rgba(255, 255, 255, 0.8)';
    }
    
    lastScroll = currentScroll;
});

// Module card hover effect - add ripple
document.querySelectorAll('.module-card-premium').forEach(card => {
    card.addEventListener('mouseenter', function(e) {
        const glow = this.querySelector('.module-glow');
        if (glow) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            glow.style.left = `${x - glow.offsetWidth / 2}px`;
            glow.style.top = `${y - glow.offsetHeight / 2}px`;
        }
    });
});

// Check API status
async function checkAPIStatus() {
    try {
        const response = await fetch('http://localhost:8000/health');
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (response.ok) {
            statusDot.style.background = '#10B981';
            statusText.textContent = 'API Online';
        } else {
            statusDot.style.background = '#F59E0B';
            statusText.textContent = 'API Warning';
        }
    } catch (error) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        statusDot.style.background = '#EF4444';
        statusText.textContent = 'API Offline';
    }
}

// Check API status on load and every 30 seconds
checkAPIStatus();
setInterval(checkAPIStatus, 30000);

// Add parallax effect to floating shapes
window.addEventListener('mousemove', (e) => {
    const shapes = document.querySelectorAll('.floating-shape');
    const mouseX = e.clientX / window.innerWidth;
    const mouseY = e.clientY / window.innerHeight;
    
    shapes.forEach((shape, index) => {
        const speed = (index + 1) * 20;
        const x = (mouseX - 0.5) * speed;
        const y = (mouseY - 0.5) * speed;
        
        shape.style.transform = `translate(${x}px, ${y}px)`;
    });
});

// Add keyboard navigation
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        // Close any open modals or overlays
    }
});

// Performance optimization: Lazy load images
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    document.querySelectorAll('img.lazy').forEach(img => imageObserver.observe(img));
}

// Add smooth reveal animation on scroll
const revealElements = document.querySelectorAll('.phase-container');
const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

revealElements.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'all 0.6s ease-out';
    revealObserver.observe(el);
});

console.log('🚀 SAKHI Premium Dashboard loaded successfully!');
