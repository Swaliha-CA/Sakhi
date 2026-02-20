"""Voice AI endpoints for speech-based screenings"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.voice_service import (
    get_bhashini_service,
    BhashiniLanguage,
    VoiceGender,
    VoiceScreeningStateMachine
)
from app.core.logging import logger

router = APIRouter()


class SpeechToTextRequest(BaseModel):
    """Request for speech-to-text conversion"""
    language: Optional[BhashiniLanguage] = None
    auto_detect: bool = True


class TextToSpeechRequest(BaseModel):
    """Request for text-to-speech conversion"""
    text: str
    language: BhashiniLanguage
    gender: VoiceGender = VoiceGender.FEMALE


class StartScreeningRequest(BaseModel):
    """Request to start voice screening"""
    screening_type: str  # "EPDS" or "PHQ9"
    language: BhashiniLanguage
    user_id: int


class ScreeningResponseRequest(BaseModel):
    """Request to process screening response"""
    session_id: str
    response_text: str
    confidence: float


# In-memory session storage (TODO: move to Redis or database)
screening_sessions: Dict[str, VoiceScreeningStateMachine] = {}


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: Optional[str] = None,
    auto_detect: bool = True
):
    """
    Convert speech to text
    
    Args:
        audio: Audio file (WAV, MP3, etc.)
        language: Target language code (optional)
        auto_detect: Auto-detect language if not specified
    
    Returns:
        Transcription with confidence score
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Convert language string to enum
        lang_enum = None
        if language:
            try:
                lang_enum = BhashiniLanguage(language)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")
        
        # Get Bhashini service
        bhashini = await get_bhashini_service()
        
        # Perform STT
        result = await bhashini.speech_to_text(
            audio_data=audio_data,
            language=lang_enum,
            auto_detect=auto_detect
        )
        
        logger.info(f"STT completed: {result['text'][:50]}... (confidence: {result['confidence']:.2%})")
        
        return result
    
    except Exception as e:
        logger.error(f"STT endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech
    
    Args:
        request: TTS request with text, language, and voice gender
    
    Returns:
        Audio file bytes
    """
    try:
        # Get Bhashini service
        bhashini = await get_bhashini_service()
        
        # Perform TTS
        audio_data = await bhashini.text_to_speech(
            text=request.text,
            language=request.language,
            gender=request.gender
        )
        
        logger.info(f"TTS completed: {len(audio_data)} bytes")
        
        return {
            "audio_data": audio_data,
            "format": "wav",
            "language": request.language.value,
            "gender": request.gender.value
        }
    
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screening/start")
async def start_screening(request: StartScreeningRequest):
    """
    Start a voice-based screening session
    
    Args:
        request: Screening start request
    
    Returns:
        Session ID and first question
    """
    try:
        # Validate screening type
        if request.screening_type not in ["EPDS", "PHQ9"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid screening type: {request.screening_type}"
            )
        
        # Create state machine
        state_machine = VoiceScreeningStateMachine(
            screening_type=request.screening_type,
            language=request.language
        )
        
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Store session
        screening_sessions[session_id] = state_machine
        
        # Get first question
        first_question = state_machine.get_current_question()
        
        logger.info(
            f"Started {request.screening_type} screening session {session_id} "
            f"for user {request.user_id} in {request.language.value}"
        )
        
        return {
            "session_id": session_id,
            "screening_type": request.screening_type,
            "language": request.language.value,
            "total_questions": len(state_machine.questions),
            "current_question": first_question
        }
    
    except Exception as e:
        logger.error(f"Start screening error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screening/respond")
async def process_screening_response(request: ScreeningResponseRequest):
    """
    Process a response to a screening question
    
    Args:
        request: Response with session ID, text, and confidence
    
    Returns:
        Processing result with next action
    """
    try:
        # Get session
        state_machine = screening_sessions.get(request.session_id)
        
        if not state_machine:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Process response
        result = state_machine.process_response(
            response_text=request.response_text,
            confidence=request.confidence
        )
        
        logger.info(f"Screening response processed: {result['status']}")
        
        # If complete, clean up session
        if result["status"] == "complete":
            del screening_sessions[request.session_id]
            logger.info(f"Screening session {request.session_id} completed")
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process response error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screening/status/{session_id}")
async def get_screening_status(session_id: str):
    """
    Get current status of a screening session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session status
    """
    try:
        state_machine = screening_sessions.get(session_id)
        
        if not state_machine:
            raise HTTPException(status_code=404, detail="Session not found")
        
        current_question = state_machine.get_current_question()
        
        return {
            "session_id": session_id,
            "screening_type": state_machine.screening_type,
            "language": state_machine.language.value,
            "current_question_number": state_machine.current_question + 1,
            "total_questions": len(state_machine.questions),
            "responses_count": len(state_machine.responses),
            "current_question": current_question,
            "is_complete": current_question is None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported languages
    
    Returns:
        List of language codes and names
    """
    bhashini = await get_bhashini_service()
    
    languages = [
        {
            "code": lang.value,
            "name": lang.name,
            "offline_supported": bhashini.is_offline_supported(lang)
        }
        for lang in BhashiniLanguage
    ]
    
    return {"languages": languages}
