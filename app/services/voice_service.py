"""Voice AI Service with Bhashini integration for multilingual speech processing"""
from typing import Optional, Dict, Any, List
from enum import Enum
import httpx
import hashlib
import json

from app.core.config import settings
from app.core.logging import logger


class BhashiniLanguage(str, Enum):
    """Supported Bhashini languages"""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"
    ODIA = "or"
    ASSAMESE = "as"


class VoiceGender(str, Enum):
    """Voice profile gender options"""
    MALE = "male"
    FEMALE = "female"


class BhashiniService:
    """
    Bhashini API integration for speech-to-text and text-to-speech
    
    Features:
    - Speech-to-text (STT) in 36+ Indic languages
    - Text-to-speech (TTS) with regional voice profiles
    - Automatic language detection
    - Confidence scoring for transcriptions
    - Offline language models for top 5 languages (TODO)
    """
    
    # Confidence threshold for flagging low-quality transcriptions
    CONFIDENCE_THRESHOLD = 0.80
    
    def __init__(self):
        """Initialize Bhashini service"""
        self.http_client: Optional[httpx.AsyncClient] = None
        self.api_key = settings.BHASHINI_API_KEY
        self.api_url = settings.BHASHINI_API_URL
        
        # Top 5 languages for offline support
        self.offline_languages = [
            BhashiniLanguage.HINDI,
            BhashiniLanguage.TAMIL,
            BhashiniLanguage.TELUGU,
            BhashiniLanguage.BENGALI,
            BhashiniLanguage.MARATHI
        ]
    
    async def connect(self):
        """Initialize HTTP client"""
        self.http_client = httpx.AsyncClient(timeout=60.0)
        logger.info("Bhashini service connected")
    
    async def disconnect(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Bhashini service disconnected")
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        language: Optional[BhashiniLanguage] = None,
        auto_detect: bool = True
    ) -> Dict[str, Any]:
        """
        Convert speech to text using Bhashini STT
        
        Args:
            audio_data: Audio file bytes (WAV, MP3, etc.)
            language: Target language (if known)
            auto_detect: Auto-detect language if not specified
        
        Returns:
            Dictionary with transcription and metadata
        """
        if not self.http_client:
            await self.connect()
        
        try:
            # Detect language if not specified
            if not language and auto_detect:
                language = await self._detect_language(audio_data)
                logger.info(f"Auto-detected language: {language}")
            
            # TODO: Implement actual Bhashini API call
            # For now, return mock response
            transcription = self._mock_stt(audio_data, language)
            
            # Check confidence threshold
            confidence = transcription.get("confidence", 1.0)
            low_confidence = confidence < self.CONFIDENCE_THRESHOLD
            
            if low_confidence:
                logger.warning(
                    f"Low confidence transcription: {confidence:.2%} "
                    f"(threshold: {self.CONFIDENCE_THRESHOLD:.2%})"
                )
            
            return {
                "text": transcription.get("text", ""),
                "language": language.value if language else "unknown",
                "confidence": confidence,
                "low_confidence_warning": low_confidence,
                "duration_seconds": transcription.get("duration", 0),
                "words": transcription.get("words", [])
            }
        
        except Exception as e:
            logger.error(f"Speech-to-text failed: {e}")
            return {
                "text": "",
                "language": language.value if language else "unknown",
                "confidence": 0.0,
                "low_confidence_warning": True,
                "error": str(e)
            }
    
    async def text_to_speech(
        self,
        text: str,
        language: BhashiniLanguage,
        gender: VoiceGender = VoiceGender.FEMALE
    ) -> bytes:
        """
        Convert text to speech using Bhashini TTS
        
        Args:
            text: Text to convert
            language: Target language
            gender: Voice gender preference
        
        Returns:
            Audio data bytes (WAV format)
        """
        if not self.http_client:
            await self.connect()
        
        try:
            # TODO: Implement actual Bhashini API call
            # For now, return empty audio
            logger.info(f"TTS: '{text[:50]}...' in {language.value} ({gender.value} voice)")
            
            return b""  # Mock empty audio
        
        except Exception as e:
            logger.error(f"Text-to-speech failed: {e}")
            return b""
    
    async def _detect_language(self, audio_data: bytes) -> BhashiniLanguage:
        """
        Auto-detect language from audio
        
        Args:
            audio_data: Audio file bytes
        
        Returns:
            Detected language
        """
        # TODO: Implement actual language detection
        # For now, default to Hindi
        return BhashiniLanguage.HINDI
    
    def _mock_stt(self, audio_data: bytes, language: Optional[BhashiniLanguage]) -> Dict[str, Any]:
        """Mock STT response for testing"""
        return {
            "text": "Mock transcription",
            "confidence": 0.95,
            "duration": 5.0,
            "words": [
                {"word": "Mock", "start": 0.0, "end": 0.5, "confidence": 0.95},
                {"word": "transcription", "start": 0.5, "end": 1.5, "confidence": 0.95}
            ]
        }
    
    def is_offline_supported(self, language: BhashiniLanguage) -> bool:
        """
        Check if language has offline support
        
        Args:
            language: Language to check
        
        Returns:
            True if offline models available
        """
        return language in self.offline_languages


class VoiceScreeningStateMachine:
    """
    State machine for voice-based screening workflows
    
    Manages EPDS and PHQ-9 screening questions with:
    - Context-aware follow-ups
    - Retry logic for unclear responses
    - Confirmation prompts for critical data
    """
    
    # EPDS questions (Edinburgh Postnatal Depression Scale)
    EPDS_QUESTIONS = [
        {
            "id": 1,
            "text": "I have been able to laugh and see the funny side of things",
            "options": ["As much as I always could", "Not quite so much now", "Definitely not so much now", "Not at all"]
        },
        {
            "id": 2,
            "text": "I have looked forward with enjoyment to things",
            "options": ["As much as I ever did", "Rather less than I used to", "Definitely less than I used to", "Hardly at all"]
        },
        {
            "id": 3,
            "text": "I have blamed myself unnecessarily when things went wrong",
            "options": ["Yes, most of the time", "Yes, some of the time", "Not very often", "No, never"]
        },
        {
            "id": 4,
            "text": "I have been anxious or worried for no good reason",
            "options": ["No, not at all", "Hardly ever", "Yes, sometimes", "Yes, very often"]
        },
        {
            "id": 5,
            "text": "I have felt scared or panicky for no very good reason",
            "options": ["Yes, quite a lot", "Yes, sometimes", "No, not much", "No, not at all"]
        },
        {
            "id": 6,
            "text": "Things have been getting on top of me",
            "options": ["Yes, most of the time I haven't been able to cope", "Yes, sometimes I haven't been coping as well as usual", "No, most of the time I have coped quite well", "No, I have been coping as well as ever"]
        },
        {
            "id": 7,
            "text": "I have been so unhappy that I have had difficulty sleeping",
            "options": ["Yes, most of the time", "Yes, sometimes", "Not very often", "No, not at all"]
        },
        {
            "id": 8,
            "text": "I have felt sad or miserable",
            "options": ["Yes, most of the time", "Yes, quite often", "Not very often", "No, not at all"]
        },
        {
            "id": 9,
            "text": "I have been so unhappy that I have been crying",
            "options": ["Yes, most of the time", "Yes, quite often", "Only occasionally", "No, never"]
        },
        {
            "id": 10,
            "text": "The thought of harming myself has occurred to me",
            "options": ["Yes, quite often", "Sometimes", "Hardly ever", "Never"],
            "critical": True  # Flag for immediate attention
        }
    ]
    
    # PHQ-9 questions (Patient Health Questionnaire)
    PHQ9_QUESTIONS = [
        {
            "id": 1,
            "text": "Little interest or pleasure in doing things",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 2,
            "text": "Feeling down, depressed, or hopeless",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 3,
            "text": "Trouble falling or staying asleep, or sleeping too much",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 4,
            "text": "Feeling tired or having little energy",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 5,
            "text": "Poor appetite or overeating",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 6,
            "text": "Feeling bad about yourself or that you are a failure",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 7,
            "text": "Trouble concentrating on things",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 8,
            "text": "Moving or speaking slowly, or being fidgety or restless",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        },
        {
            "id": 9,
            "text": "Thoughts that you would be better off dead or hurting yourself",
            "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
            "critical": True
        }
    ]
    
    def __init__(self, screening_type: str, language: BhashiniLanguage):
        """
        Initialize screening state machine
        
        Args:
            screening_type: "EPDS" or "PHQ9"
            language: Language for questions
        """
        self.screening_type = screening_type
        self.language = language
        self.current_question = 0
        self.responses: Dict[int, int] = {}
        self.retry_count = 0
        self.max_retries = 3
        
        # Select question set
        if screening_type == "EPDS":
            self.questions = self.EPDS_QUESTIONS
        elif screening_type == "PHQ9":
            self.questions = self.PHQ9_QUESTIONS
        else:
            raise ValueError(f"Unknown screening type: {screening_type}")
    
    def get_current_question(self) -> Optional[Dict[str, Any]]:
        """
        Get current question
        
        Returns:
            Question dictionary or None if complete
        """
        if self.current_question >= len(self.questions):
            return None
        
        return self.questions[self.current_question]
    
    def process_response(self, response_text: str, confidence: float) -> Dict[str, Any]:
        """
        Process voice response to current question
        
        Args:
            response_text: Transcribed response
            confidence: Transcription confidence
        
        Returns:
            Processing result with next action
        """
        question = self.get_current_question()
        
        if not question:
            return {"status": "complete", "message": "Screening complete"}
        
        # Check if confidence is too low
        if confidence < 0.7:
            self.retry_count += 1
            
            if self.retry_count >= self.max_retries:
                return {
                    "status": "retry_exceeded",
                    "message": "Could not understand response after multiple attempts",
                    "action": "skip_question"
                }
            
            return {
                "status": "unclear",
                "message": "I didn't understand that clearly. Could you please repeat?",
                "action": "retry",
                "retry_count": self.retry_count
            }
        
        # Parse response (map to option index)
        option_index = self._parse_response(response_text, question["options"])
        
        if option_index is None:
            self.retry_count += 1
            
            if self.retry_count >= self.max_retries:
                return {
                    "status": "retry_exceeded",
                    "message": "Could not match response to options",
                    "action": "skip_question"
                }
            
            return {
                "status": "unclear",
                "message": f"Please choose one of: {', '.join(question['options'])}",
                "action": "retry",
                "retry_count": self.retry_count
            }
        
        # Store response
        self.responses[question["id"]] = option_index
        self.retry_count = 0
        
        # Check if critical question
        if question.get("critical") and option_index >= 2:  # High-risk response
            return {
                "status": "critical_response",
                "message": "This response indicates high risk. Immediate follow-up needed.",
                "action": "flag_for_review",
                "question_id": question["id"],
                "response_index": option_index
            }
        
        # Move to next question
        self.current_question += 1
        
        if self.current_question >= len(self.questions):
            return {
                "status": "complete",
                "message": "Screening complete",
                "total_score": self.calculate_score(),
                "responses": self.responses
            }
        
        return {
            "status": "continue",
            "message": "Response recorded",
            "next_question": self.get_current_question()
        }
    
    def _parse_response(self, response_text: str, options: List[str]) -> Optional[int]:
        """
        Parse voice response to match option index
        
        Args:
            response_text: Transcribed response
            options: Available options
        
        Returns:
            Option index (0-based) or None if no match
        """
        response_lower = response_text.lower().strip()
        
        # Try exact match
        for i, option in enumerate(options):
            if option.lower() in response_lower:
                return i
        
        # Try number matching (1-4 or 0-3)
        for i in range(len(options)):
            if str(i) in response_lower or str(i + 1) in response_lower:
                return i
        
        # Try keyword matching
        keywords = {
            0: ["never", "not at all", "no", "none"],
            1: ["rarely", "hardly", "sometimes", "little"],
            2: ["often", "quite", "more", "several"],
            3: ["always", "most", "very", "nearly", "every"]
        }
        
        for index, words in keywords.items():
            if index < len(options) and any(word in response_lower for word in words):
                return index
        
        return None
    
    def calculate_score(self) -> int:
        """
        Calculate total screening score
        
        Returns:
            Total score
        """
        return sum(self.responses.values())
    
    def get_risk_level(self) -> str:
        """
        Determine risk level based on score
        
        Returns:
            Risk level string
        """
        score = self.calculate_score()
        
        if self.screening_type == "EPDS":
            # EPDS scoring: 0-9 low, 10-12 moderate, 13+ high
            if score >= 13:
                return "high"
            elif score >= 10:
                return "moderate"
            else:
                return "low"
        
        elif self.screening_type == "PHQ9":
            # PHQ-9 scoring: 0-4 minimal, 5-9 mild, 10-14 moderate, 15-19 moderately severe, 20-27 severe
            if score >= 20:
                return "severe"
            elif score >= 15:
                return "moderately_severe"
            elif score >= 10:
                return "moderate"
            elif score >= 5:
                return "mild"
            else:
                return "minimal"
        
        return "unknown"


# Global Bhashini service instance
bhashini_service: Optional[BhashiniService] = None


async def get_bhashini_service() -> BhashiniService:
    """
    Get or create global Bhashini service instance
    
    Returns:
        BhashiniService instance
    """
    global bhashini_service
    
    if bhashini_service is None:
        bhashini_service = BhashiniService()
        await bhashini_service.connect()
        logger.info("Bhashini service initialized")
    
    return bhashini_service
