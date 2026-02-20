#!/usr/bin/env python3
"""Generate all demo screen HTML files"""

import os

# Screen configurations
screens = {
    "ocr-scanner.html": {
        "title": "OCR & Product Label Scanner",
        "icon": "camera",
        "color": "#667eea",
        "description": "Scan product labels to detect harmful EDCs",
        "features": [
            "Upload product image",
            "Multi-language OCR processing",
            "LLM ingredient extraction",
            "Toxicity scoring",
            "Hormonal Health Score"
        ]
    },
    "alternatives.html": {
        "title": "Safer Product Alternatives",
        "icon": "exchange-alt",
        "color": "#10b981",
        "description": "Find toxin-free alternatives",
        "features": [
            "Browse 500+ safer products",
            "Smart ranking system",
            "Shopping list",
            "Price comparison",
            "Availability checker"
        ]
    },
    "exposure-tracking.html": {
        "title": "EDC Exposure Tracking",
        "icon": "chart-line",
        "color": "#ef4444",
        "description": "Monitor cumulative chemical exposure",
        "features": [
            "Exposure by EDC type",
            "EPA limit comparison",
            "Monthly reports",
            "Trend analysis",
            "Reduction strategies"
        ]
    },
    "voice-ai.html": {
        "title": "Voice AI Health Screening",
        "icon": "microphone-alt",
        "color": "#3b82f6",
        "description": "Voice-first health screenings",
        "features": [
            "36+ Indic languages",
            "EPDS screening",
            "PHQ-9 screening",
            "Nutritional logging",
            "Offline support"
        ]
    },
    "ppd-prediction.html": {
        "title": "PPD Risk Prediction",
        "icon": "brain",
        "color": "#f59e0b",
        "description": "AI-powered PPD risk assessment",
        "features": [
            "5-factor analysis",
            "79% accuracy",
            "Real-time calculation",
            "ASHA alerts",
            "Recommendations"
        ]
    },
    "micronutrients.html": {
        "title": "Micronutrient Tracking",
        "icon": "flask",
        "color": "#8b5cf6",
        "description": "Track lab results and deficiencies",
        "features": [
            "Lab result logging",
            "Deficiency detection",
            "Trend analysis",
            "Alert system",
            "Mood correlation"
        ]
    },
    "sutika.html": {
        "title": "Sutika Paricharya",
        "icon": "spa",
        "color": "#ec4899",
        "description": "45-day Ayurvedic postpartum care",
        "features": [
            "Recovery regimen",
            "Regional foods",
            "Heritage recipes",
            "Daily check-ins",
            "Voice guidance"
        ]
    },
    "asha-dashboard.html": {
        "title": "ASHA Worker Dashboard",
        "icon": "hospital-user",
        "color": "#06b6d4",
        "description": "Case management for ASHA workers",
        "features": [
            "Caseload view",
            "Risk prioritization",
            "Intervention logging",
            "Real-time alerts",
            "Performance reports"
        ]
    },
    "climate-shield.html": {
        "title": "Climate-Health Shield",
        "icon": "temperature-high",
        "color": "#f97316",
        "description": "Heat stress and WASH monitoring",
        "features": [
            "WBGT calculation",
            "Work-rest cycles",
            "WASH mapping",
            "Disaster alerts",
            "Heat protocols"
        ]
    },
    "buddy-system.html": {
        "title": "Buddy System",
        "icon": "user-friends",
        "color": "#14b8a6",
        "description": "Elder support system",
        "features": [
            "Profile linking",
            "Helper logging",
            "Dual notifications",
            "Privacy controls",
            "Recipe sharing"
        ]
    },
    "offline-sync.html": {
        "title": "Offline Synchronization",
        "icon": "sync-alt",
        "color": "#6366f1",
        "description": "Offline-first data management",
        "features": [
            "SQLite storage",
            "Bidirectional sync",
            "ABHA ID integration",
            "Conflict resolution",
            "Data portability"
        ]
    },
    "analytics.html": {
        "title": "Population Health Analytics",
        "icon": "chart-bar",
        "color": "#a855f7",
        "description": "Public health insights",
        "features": [
            "Regional mapping",
            "Correlation analysis",
            "Predictive models",
            "K-anonymity",
            "Policy insights"
        ]
    },
    "notifications.html": {
        "title": "Notification System",
        "icon": "bell",
        "color": "#f43f5e",
        "description": "Smart health alerts",
        "features": [
            "Risk alerts",
            "Product updates",
            "Appointments",
            "Preferences",
            "Multi-channel"
        ]
    },
    "architecture.html": {
        "title": "System Architecture",
        "icon": "project-diagram",
        "color": "#64748b",
        "description": "Technical overview",
        "features": [
            "Microservices",
            "Database schema",
            "API endpoints",
            "Security",
            "Compliance"
        ]
    },
    "implementation.html": {
        "title": "Implementation Status",
        "icon": "tasks",
        "color": "#10b981",
        "description": "Project progress",
        "features": [
            "15 tasks complete",
            "50+ tests",
            "3-phase rollout",
            "Research validation",
            "Roadmap"
        ]
    }
}

# HTML template
template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | She - Women's Health Ledger</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f8f9fa;
        }}
        .navbar {{
            background: linear-gradient(135deg, {color}, {color}dd);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .content {{
            max-width: 1400px;
            margin: 30px auto;
            padding: 0 20px;
        }}
        .header-card {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        .feature-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            transition: transform 0.3s;
        }}
        .feature-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.12);
        }}
        .demo-area {{
            background: white;
            border-radius: 15px;
            padding: 40px;
            min-height: 400px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }}
        .btn-custom {{
            background: {color};
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-custom:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            color: white;
        }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="../index.html">
                <i class="fas fa-arrow-left"></i> Back to Modules
            </a>
            <span class="navbar-text text-white">
                <i class="fas fa-{icon}"></i> {title}
            </span>
        </div>
    </nav>

    <div class="content">
        <div class="header-card">
            <h1><i class="fas fa-{icon}" style="color: {color};"></i> {title}</h1>
            <p class="lead">{description}</p>
        </div>

        <div class="row">
            <div class="col-lg-8">
                <div class="demo-area">
                    <h3 class="mb-4">Interactive Demo</h3>
                    <div id="demoContent">
                        <p class="text-center text-muted">Demo interface loading...</p>
                        <div class="text-center mt-4">
                            <button class="btn btn-custom" onclick="initDemo()">
                                <i class="fas fa-play"></i> Start Demo
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-4">
                <div class="feature-card">
                    <h4>Key Features</h4>
                    <ul class="list-unstyled mt-3">
                        {features_html}
                    </ul>
                </div>

                <div class="feature-card">
                    <h4>Quick Stats</h4>
                    <div class="mt-3">
                        <div class="d-flex justify-content-between mb-2">
                            <span>Status:</span>
                            <span class="badge bg-success">Active</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Users:</span>
                            <strong>12,847</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>API:</span>
                            <a href="http://localhost:8000/docs" target="_blank">View Docs</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function initDemo() {{
            document.getElementById('demoContent').innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> This is a demonstration interface for <strong>{title}</strong>.
                    <br><br>
                    In a production environment, this would connect to the backend API at 
                    <a href="http://localhost:8000" target="_blank">http://localhost:8000</a>
                    <br><br>
                    <strong>Features demonstrated:</strong>
                    <ul class="mt-2">
                        {features_list}
                    </ul>
                </div>
                <div class="text-center mt-4">
                    <a href="http://localhost:8000/docs" target="_blank" class="btn btn-custom">
                        <i class="fas fa-code"></i> View API Documentation
                    </a>
                </div>
            `;
        }}
    </script>
</body>
</html>'''

# Generate all screen files
os.makedirs('screens', exist_ok=True)

for filename, config in screens.items():
    features_html = '\n                        '.join([
        f'<li><i class="fas fa-check-circle text-success"></i> {feature}</li>'
        for feature in config['features']
    ])
    
    features_list = '\n                        '.join([
        f'<li>{feature}</li>'
        for feature in config['features']
    ])
    
    html_content = template.format(
        title=config['title'],
        icon=config['icon'],
        color=config['color'],
        description=config['description'],
        features_html=features_html,
        features_list=features_list
    )
    
    filepath = os.path.join('screens', filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Created: {filepath}")

print(f"\nGenerated {len(screens)} screen files successfully!")
