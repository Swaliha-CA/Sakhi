// Voice AI Component
const VoiceComponent = {
    mediaRecorder: null,
    audioChunks: [],
    isRecording: false,
    sessionId: null,
    currentScreening: null,

    render() {
        return `
            <div class="section-container">
                <div class="row">
                    <div class="col-lg-8 mx-auto">
                        <div class="card">
                            <div class="card-header">
                                <h3><i class="fas fa-microphone-alt"></i> Voice AI Health Screening</h3>
                            </div>
                            <div class="card-body">
                                <div class="row mb-4">
                                    <div class="col-md-6">
                                        <label class="form-label">Select Language</label>
                                        <select class="form-select" id="voiceLanguageSelect">
                                            <option value="en">English</option>
                                            <option value="hi">Hindi (हिंदी)</option>
                                            <option value="ta">Tamil (தமிழ்)</option>
                                            <option value="te">Telugu (తెలుగు)</option>
                                            <option value="bn">Bengali (বাংলা)</option>
                                            <option value="ml">Malayalam (മലയാളം)</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Screening Type</label>
                                        <select class="form-select" id="screeningTypeSelect">
                                            <option value="EPDS">EPDS (Postpartum Depression)</option>
                                            <option value="PHQ9">PHQ-9 (General Depression)</option>
                                        </select>
                                    </div>
                                </div>

                                <div class="text-center mb-4">
                                    <button class="btn btn-primary btn-lg" id="startScreeningBtn">
                                        <i class="fas fa-play"></i> Start Screening
                                    </button>
                                </div>

                                <div id="screeningInterface" style="display: none;">
                                    <div class="alert alert-info" id="currentQuestion">
                                        Question will appear here...
                                    </div>

                                    <div class="text-center mb-4">
                                        <button class="voice-button" id="recordBtn">
                                            <i class="fas fa-microphone"></i>
                                        </button>
                                        <p class="mt-2 text-muted">Tap to speak</p>
                                    </div>

                                    <div class="mb-3">
                                        <label class="form-label">Progress</label>
                                        <div class="progress">
                                            <div class="progress-bar" id="screeningProgress" style="width: 0%">0%</div>
                                        </div>
                                        <small class="text-muted" id="progressText">Question 0 of 0</small>
                                    </div>

                                    <div id="transcriptionResult" class="alert alert-secondary" style="display: none;">
                                        <strong>You said:</strong> <span id="transcriptionText"></span>
                                    </div>
                                </div>

                                <div id="screeningResults" style="display: none;">
                                    <div class="result-card">
                                        <h4 class="text-center mb-4">Screening Complete</h4>
                                        <div class="text-center mb-4">
                                            <div class="score-badge" id="screeningScore">--</div>
                                            <p class="text-muted mt-2">Total Score</p>
                                        </div>
                                        <div id="screeningRecommendations"></div>
                                        <button class="btn btn-primary w-100 mt-3" onclick="VoiceComponent.resetScreening()">
                                            <i class="fas fa-redo"></i> Start New Screening
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init() {
        document.getElementById('startScreeningBtn').addEventListener('click', () => this.startScreening());
        document.getElementById('recordBtn').addEventListener('click', () => this.toggleRecording());
    },

    async startScreening() {
        const language = document.getElementById('voiceLanguageSelect').value;
        const screeningType = document.getElementById('screeningTypeSelect').value;

        utils.showLoading();

        try {
            const result = await api.startScreening(screeningType, language, APP_CONFIG.USER_ID);
            
            this.sessionId = result.session_id;
            this.currentScreening = result;

            document.getElementById('startScreeningBtn').style.display = 'none';
            document.getElementById('screeningInterface').style.display = 'block';

            this.displayQuestion(result.current_question);
            this.updateProgress(1, result.total_questions);

            utils.showToast('Screening started', 'success');
        } catch (error) {
            console.error('Start screening error:', error);
            utils.showToast('Failed to start screening: ' + error.message, 'error');
        } finally {
            utils.hideLoading();
        }
    },

    displayQuestion(question) {
        if (!question) return;
        document.getElementById('currentQuestion').innerHTML = `
            <strong>Question ${question.number}:</strong><br>
            ${question.text}
        `;
    },

    updateProgress(current, total) {
        const percentage = (current / total) * 100;
        document.getElementById('screeningProgress').style.width = percentage + '%';
        document.getElementById('screeningProgress').textContent = Math.round(percentage) + '%';
        document.getElementById('progressText').textContent = `Question ${current} of ${total}`;
    },

    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    },

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.processAudio(audioBlob);
            };

            this.mediaRecorder.start();
            this.isRecording = true;

            const recordBtn = document.getElementById('recordBtn');
            recordBtn.classList.add('recording');
            recordBtn.innerHTML = '<i class="fas fa-stop"></i>';

            utils.showToast('Recording...', 'info');
        } catch (error) {
            console.error('Recording error:', error);
            utils.showToast('Microphone access denied', 'error');
        }
    },

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.isRecording = false;

            const recordBtn = document.getElementById('recordBtn');
            recordBtn.classList.remove('recording');
            recordBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        }
    },

    async processAudio(audioBlob) {
        utils.showLoading();

        try {
            const language = document.getElementById('voiceLanguageSelect').value;
            const sttResult = await api.speechToText(audioBlob, language);

            // Display transcription
            document.getElementById('transcriptionText').textContent = sttResult.text;
            document.getElementById('transcriptionResult').style.display = 'block';

            // Process response
            const response = await api.respondToScreening(
                this.sessionId,
                sttResult.text,
                sttResult.confidence
            );

            if (response.status === 'complete') {
                this.displayResults(response);
            } else if (response.status === 'next_question') {
                this.displayQuestion(response.next_question);
                this.updateProgress(response.current_question_number, response.total_questions);
            }

        } catch (error) {
            console.error('Process audio error:', error);
            utils.showToast('Failed to process audio: ' + error.message, 'error');
        } finally {
            utils.hideLoading();
        }
    },

    displayResults(response) {
        document.getElementById('screeningInterface').style.display = 'none';
        document.getElementById('screeningResults').style.display = 'block';

        const score = response.total_score || 0;
        const scoreElement = document.getElementById('screeningScore');
        scoreElement.textContent = score;
        scoreElement.className = 'score-badge ' + (score < 10 ? 'score-safe' : score < 20 ? 'score-warning' : 'score-danger');

        const recommendations = document.getElementById('screeningRecommendations');
        recommendations.innerHTML = `
            <div class="alert ${score < 10 ? 'alert-success' : score < 20 ? 'alert-warning' : 'alert-danger'}">
                <h5>${response.risk_level || 'Assessment Complete'}</h5>
                <p>${response.recommendation || 'Thank you for completing the screening.'}</p>
            </div>
        `;

        utils.showToast('Screening completed', 'success');
    },

    resetScreening() {
        this.sessionId = null;
        this.currentScreening = null;
        document.getElementById('startScreeningBtn').style.display = 'block';
        document.getElementById('screeningInterface').style.display = 'none';
        document.getElementById('screeningResults').style.display = 'none';
        document.getElementById('transcriptionResult').style.display = 'none';
    }
};

window.VoiceComponent = VoiceComponent;
