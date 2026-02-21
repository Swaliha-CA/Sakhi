// Home Component
const HomeComponent = {
    render() {
        return `
            <div class="section-container">
                <div class="hero-section">
                    <h1><i class="fas fa-heartbeat"></i> SAKHI</h1>
                    <p class="lead">सखी - Your Trusted Health Friend</p>
                    <p>Comprehensive women's health platform with AI-powered insights</p>
                </div>

                <div class="feature-grid">
                    <div class="feature-card" onclick="app.navigate('ocr')">
                        <div class="feature-icon">
                            <i class="fas fa-camera"></i>
                        </div>
                        <h3>OCR Scanner</h3>
                        <p>Scan product labels to detect harmful chemicals</p>
                    </div>

                    <div class="feature-card" onclick="app.navigate('alternatives')">
                        <div class="feature-icon">
                            <i class="fas fa-exchange-alt"></i>
                        </div>
                        <h3>Safer Alternatives</h3>
                        <p>Find toxin-free product alternatives</p>
                    </div>

                    <div class="feature-card" onclick="app.navigate('voice')">
                        <div class="feature-icon">
                            <i class="fas fa-microphone-alt"></i>
                        </div>
                        <h3>Voice AI</h3>
                        <p>Voice-based health screenings in multiple languages</p>
                    </div>

                    <div class="feature-card" onclick="app.navigate('notifications')">
                        <div class="feature-icon">
                            <i class="fas fa-bell"></i>
                        </div>
                        <h3>Notifications</h3>
                        <p>Stay updated with health alerts and product updates</p>
                    </div>
                </div>

                <div class="row mt-5">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body text-center">
                                <h2 class="text-primary">15</h2>
                                <p class="text-muted">Complete Modules</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body text-center">
                                <h2 class="text-success">36</h2>
                                <p class="text-muted">Languages Supported</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body text-center">
                                <h2 class="text-info">500+</h2>
                                <p class="text-muted">Safer Products</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init() {
        // No initialization needed for home page
    }
};

window.HomeComponent = HomeComponent;
