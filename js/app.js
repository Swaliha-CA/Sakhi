// Main Application
class App {
    constructor() {
        this.currentPage = 'home';
        this.components = {
            home: HomeComponent,
            ocr: OCRComponent,
            alternatives: AlternativesComponent,
            voice: VoiceComponent,
            notifications: NotificationsComponent
        };
    }

    init() {
        // Set up navigation
        this.setupNavigation();
        
        // Load initial page
        this.navigate('home');
        
        // Check API status
        utils.checkAPIStatus();
    }

    setupNavigation() {
        // Handle navigation clicks
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const href = e.target.getAttribute('href');
                if (href && href.startsWith('#')) {
                    e.preventDefault();
                    const page = href.substring(1);
                    this.navigate(page);
                }
            });
        });

        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page) {
                this.loadPage(e.state.page);
            }
        });
    }

    navigate(page) {
        // Update URL
        history.pushState({ page }, '', `#${page}`);
        
        // Load page
        this.loadPage(page);
    }

    loadPage(page) {
        // Validate page
        if (!this.components[page]) {
            page = 'home';
        }

        this.currentPage = page;

        // Update active nav link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${page}`) {
                link.classList.add('active');
            }
        });

        // Render component
        const component = this.components[page];
        const content = document.getElementById('app-content');
        content.innerHTML = component.render();

        // Initialize component
        if (component.init) {
            component.init();
        }

        // Scroll to top
        window.scrollTo(0, 0);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    window.app.init();
});
