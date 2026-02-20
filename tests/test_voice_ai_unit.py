"""
Unit tests for Voice AI service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.voice_service import VoiceService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def voice_service(mock_db_session):
    """Create a VoiceService instance."""
    return VoiceService(mock_db_session)


class TestSTTTTSIntegration:
    """Test speech-to-text and text-to-speech API integration."""
    
    @pytest.mark.asyncio
    async def test_speech_to_text(self, voice_service):
        """Test speech-to-text conversion."""
        with patch.object(voice_service, '_call_bhashini_stt', new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = {
                'text': 'Hello world',
                'confidence': 0.95,
                'language': 'en'
            }
            
            result = await voice_service.speech_to_text(
                audio_data=b'fake_audio',
                language='en'
            )
            
            assert result['text'] == 'Hello world'
            assert result['confidence'] == 0.95
    
    @pytest.mark.asyncio
    async def test_text_to_speech(self, voice_service):
        """Test text-to-speech conversion."""
        with patch.object(voice_service, '_call_bhashini_tts', new_callable=AsyncMock) as mock_tts:
            mock_tts.return_value = {
                'audio': b'fake_audio_output',
                'duration': 2.5
            }
            
            result = await voice_service.text_to_speech(
                text='Hello world',
                language='en',
                voice_profile='female'
            )
            
            assert 'audio' in result
            assert result['duration'] == 2.5


class TestLanguageDetection:
    """Test language detection and selection."""
    
    @pytest.mark.asyncio
    async def test_language_detection(self, voice_service):
        """Test automatic language detection."""
        with patch.object(voice_service, '_detect_language', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = 'hi'
            
            result = await voice_service.detect_language(audio_data=b'fake_audio')
            
            assert result == 'hi'
    
    def test_supported_languages(self, voice_service):
        """Test that all required Indic languages are supported."""
        supported = voice_service.get_supported_languages()
        
        # Must support major Indic languages
        required_languages = ['hi', 'ta', 'te', 'bn', 'en']
        for lang in required_languages:
            assert lang in supported


class TestScreeningStateMachines:
    """Test screening state machines."""
    
    @pytest.mark.asyncio
    async def test_epds_screening_flow(self, voice_service, mock_db_session):
        """Test EPDS screening question flow."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await voice_service.start_screening(
            user_id='user123',
            screening_type='EPDS',
            language='en'
        )
        
        assert result['screening_type'] == 'EPDS'
        assert result['current_question'] == 0
        assert result['total_questions'] == 10
    
    @pytest.mark.asyncio
    async def test_phq9_screening_flow(self, voice_service, mock_db_session):
        """Test PHQ-9 screening question flow."""
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=None)
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await voice_service.start_screening(
            user_id='user123',
            screening_type='PHQ-9',
            language='hi'
        )
        
        assert result['screening_type'] == 'PHQ-9'
        assert result['current_question'] == 0
        assert result['total_questions'] == 9
    
    @pytest.mark.asyncio
    async def test_screening_response_recording(self, voice_service, mock_db_session):
        """Test recording screening responses."""
        mock_session = Mock(current_question=0, responses=[])
        mock_db_session.execute = AsyncMock(return_value=Mock(
            scalar_one_or_none=Mock(return_value=mock_session)
        ))
        mock_db_session.commit = AsyncMock()
        
        result = await voice_service.record_response(
            session_id='session123',
            response=2
        )
        
        assert result['success'] is True


class TestRetryAndConfirmation:
    """Test retry logic and confirmation prompts."""
    
    @pytest.mark.asyncio
    async def test_retry_on_low_confidence(self, voice_service):
        """Test retry logic for unclear responses."""
        with patch.object(voice_service, '_call_bhashini_stt', new_callable=AsyncMock) as mock_stt:
            # First attempt: low confidence
            mock_stt.return_value = {
                'text': 'unclear',
                'confidence': 0.65
            }
            
            result = await voice_service.speech_to_text(
                audio_data=b'fake_audio',
                language='en'
            )
            
            # Should flag for retry
            assert result['confidence'] < 0.8
    
    @pytest.mark.asyncio
    async def test_confirmation_for_critical_data(self, voice_service, mock_db_session):
        """Test confirmation prompts for critical data."""
        result = await voice_service.request_confirmation(
            data={'response': 3, 'question': 'suicidal thoughts'},
            language='en'
        )
        
        assert 'confirmation_prompt' in result
        assert result['requires_confirmation'] is True


class TestNutritionalLogging:
    """Test nutritional logging via voice."""
    
    @pytest.mark.asyncio
    async def test_voice_food_logging(self, voice_service, mock_db_session):
        """Test logging food intake via voice."""
        mock_db_session.commit = AsyncMock()
        
        with patch.object(voice_service, 'speech_to_text', new_callable=AsyncMock) as mock_stt:
            mock_stt.return_value = {
                'text': 'I ate 2 rotis and 1 cup dal',
                'confidence': 0.92
            }
            
            result = await voice_service.log_nutrition_voice(
                user_id='user123',
                audio_data=b'fake_audio',
                language='hi'
            )
            
            assert result['success'] is True
            assert 'parsed_items' in result
    
    @pytest.mark.asyncio
    async def test_food_item_extraction(self, voice_service):
        """Test extracting food items from voice input."""
        text = "I ate 2 rotis, 1 cup dal, and 100 grams paneer"
        
        result = await voice_service.extract_food_items(text)
        
        assert isinstance(result, list)
        assert len(result) > 0


class TestOfflineMode:
    """Test offline mode fallback."""
    
    @pytest.mark.asyncio
    async def test_offline_language_models(self, voice_service):
        """Test offline language model fallback."""
        with patch.object(voice_service, '_is_online', return_value=False):
            with patch.object(voice_service, '_use_offline_model', new_callable=AsyncMock) as mock_offline:
                mock_offline.return_value = {
                    'text': 'offline transcription',
                    'confidence': 0.85
                }
                
                result = await voice_service.speech_to_text(
                    audio_data=b'fake_audio',
                    language='hi'
                )
                
                assert result['text'] == 'offline transcription'
    
    def test_offline_supported_languages(self, voice_service):
        """Test that top 5 languages have offline support."""
        offline_languages = voice_service.get_offline_supported_languages()
        
        # Top 5 languages should have offline support
        top_languages = ['hi', 'ta', 'te', 'bn', 'en']
        for lang in top_languages:
            assert lang in offline_languages
