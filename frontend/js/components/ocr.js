// OCR Scanner Component
const OCRComponent = {
    selectedFile: null,
    selectedLanguage: null,

    render() {
        return `
            <div class="section-container">
                <div class="row">
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h3><i class="fas fa-camera"></i> OCR Product Scanner</h3>
                            </div>
                            <div class="card-body">
                                <div class="upload-zone" id="uploadZone">
                                    <i class="fas fa-cloud-upload-alt fa-3x text-primary mb-3"></i>
                                    <h5>Drop image here or click to upload</h5>
                                    <p class="text-muted">Supports JPG, PNG, WebP (Max 5MB)</p>
                                    <input type="file" id="fileInput" accept="image/*" style="display: none;">
                                </div>

                                <div class="mt-3">
                                    <label class="form-label">Language (Optional)</label>
                                    <select class="form-select" id="languageSelect">
                                        <option value="">Auto-detect</option>
                                        <option value="en">English</option>
                                        <option value="hi">Hindi</option>
                                        <option value="ta">Tamil</option>
                                        <option value="te">Telugu</option>
                                        <option value="bn">Bengali</option>
                                    </select>
                                </div>

                                <div class="mt-3" id="imagePreview" style="display: none;">
                                    <img id="previewImg" class="img-fluid rounded" style="max-height: 300px;">
                                </div>

                                <button class="btn btn-primary btn-lg w-100 mt-3" id="scanBtn" disabled>
                                    <i class="fas fa-search"></i> Scan Product
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-6">
                        <div id="resultsContainer" style="display: none;">
                            <div class="card">
                                <div class="card-header">
                                    <h3><i class="fas fa-chart-bar"></i> Scan Results</h3>
                                </div>
                                <div class="card-body">
                                    <div class="text-center mb-4">
                                        <div class="score-badge" id="toxicityScore">--</div>
                                        <p class="text-muted mt-2">Toxicity Score</p>
                                    </div>

                                    <div class="mb-3">
                                        <h5>Extracted Text</h5>
                                        <div class="alert alert-info" id="extractedText">--</div>
                                    </div>

                                    <div class="mb-3">
                                        <h5>Detected Chemicals</h5>
                                        <div id="chemicalsList">--</div>
                                    </div>

                                    <div class="mb-3">
                                        <h5>Confidence Score</h5>
                                        <div class="progress">
                                            <div class="progress-bar" id="confidenceBar" style="width: 0%">0%</div>
                                        </div>
                                    </div>

                                    <button class="btn btn-success w-100" id="findAlternativesBtn">
                                        <i class="fas fa-exchange-alt"></i> Find Safer Alternatives
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const scanBtn = document.getElementById('scanBtn');
        const languageSelect = document.getElementById('languageSelect');

        // Click to upload
        uploadZone.addEventListener('click', () => fileInput.click());

        // File selection
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });

        // Drag and drop
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            this.handleFileSelect(e.dataTransfer.files[0]);
        });

        // Language selection
        languageSelect.addEventListener('change', (e) => {
            this.selectedLanguage = e.target.value || null;
        });

        // Scan button
        scanBtn.addEventListener('click', () => this.scanProduct());

        // Find alternatives button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'findAlternativesBtn' || e.target.closest('#findAlternativesBtn')) {
                app.navigate('alternatives');
            }
        });
    },

    handleFileSelect(file) {
        try {
            utils.validateImageFile(file);
            this.selectedFile = file;

            // Show preview
            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('previewImg').src = e.target.result;
                document.getElementById('imagePreview').style.display = 'block';
            };
            reader.readAsDataURL(file);

            // Enable scan button
            document.getElementById('scanBtn').disabled = false;

            utils.showToast('Image loaded successfully', 'success');
        } catch (error) {
            utils.showToast(error.message, 'error');
        }
    },

    async scanProduct() {
        if (!this.selectedFile) {
            utils.showToast('Please select an image first', 'warning');
            return;
        }

        utils.showLoading();

        try {
            const result = await api.extractText(this.selectedFile, this.selectedLanguage);

            if (result.success && result.data) {
                this.displayResults(result.data);
                utils.showToast('Scan completed successfully', 'success');
            } else {
                utils.showToast(result.message || 'No text detected', 'warning');
            }
        } catch (error) {
            console.error('Scan error:', error);
            utils.showToast('Scan failed: ' + error.message, 'error');
        } finally {
            utils.hideLoading();
        }
    },

    displayResults(data) {
        // Show results container
        document.getElementById('resultsContainer').style.display = 'block';

        // Calculate toxicity score (simplified)
        const toxicityScore = this.calculateToxicityScore(data);
        const scoreElement = document.getElementById('toxicityScore');
        scoreElement.textContent = toxicityScore;
        scoreElement.className = 'score-badge ' + utils.getScoreClass(100 - toxicityScore);

        // Display extracted text
        document.getElementById('extractedText').textContent = data.raw_text || 'No text detected';

        // Display chemicals (if available in future)
        const chemicalsList = document.getElementById('chemicalsList');
        chemicalsList.innerHTML = '<span class="badge bg-secondary">Analysis in progress...</span>';

        // Display confidence
        const confidence = Math.round((data.confidence || 0) * 100);
        const confidenceBar = document.getElementById('confidenceBar');
        confidenceBar.style.width = confidence + '%';
        confidenceBar.textContent = confidence + '%';

        // Scroll to results
        document.getElementById('resultsContainer').scrollIntoView({ behavior: 'smooth' });
    },

    calculateToxicityScore(data) {
        // Simplified toxicity calculation based on text length and confidence
        // In production, this would use LLM analysis
        const textLength = (data.raw_text || '').length;
        const confidence = data.confidence || 0;
        
        // Random score for demo (would be replaced with actual analysis)
        return Math.floor(Math.random() * 40) + 20; // 20-60 range
    }
};

window.OCRComponent = OCRComponent;
