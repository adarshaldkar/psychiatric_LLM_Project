"""
Voice STT API — faster-whisper backend transcription endpoint.

POST /voice/transcribe
  - Accepts multipart audio file (WebM, WAV, MP4, OGG, M4A)
  - Transcribes using faster-whisper (local, free, no API cost)
  - Returns JSON { "transcript": "...", "language": "en", "duration_s": 4.2 }

Why faster-whisper over browser Web Speech API:
  - Works in all browsers (not just Chrome)
  - Medical vocabulary: clinical psychiatric terms transcribe more accurately
  - Privacy: audio never leaves the server (no Google/Apple STT)
  - Language: multi-language support (en, hi, es, etc.)
"""
import os
import uuid
import time
import logging
import tempfile
import asyncio
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.api.auth import get_current_user
from app.models.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice STT"])

# Lazy-load the whisper model to avoid slow startup
_whisper_model = None
_whisper_lock = asyncio.Lock()

ALLOWED_AUDIO_EXTS = {'.webm', '.wav', '.mp3', '.mp4', '.ogg', '.m4a', '.flac'}
MAX_AUDIO_SIZE_MB = 25  # 25MB max audio upload


async def _get_whisper_model():
    """Lazy-load faster-whisper model once and cache globally."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    async with _whisper_lock:
        if _whisper_model is not None:
            return _whisper_model
        try:
            from faster_whisper import WhisperModel
            from app.core.config import settings

            model_size = settings.WHISPER_MODEL  # 'base' by default
            logger.info(f"Loading faster-whisper model '{model_size}'...")
            # cpu_threads=4 balances speed vs. memory on a dev machine
            _whisper_model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=4,
                num_workers=1,
            )
            logger.info(f"faster-whisper model '{model_size}' loaded successfully")
            return _whisper_model
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail=(
                    "faster-whisper is not installed. "
                    "Run: pip install faster-whisper  then restart the server."
                )
            )
        except Exception as e:
            logger.error(f"Failed to load whisper model: {e}")
            raise HTTPException(status_code=503, detail=f"Whisper model load error: {e}")


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WebM/WAV/MP4/OGG/M4A)"),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe uploaded audio using faster-whisper.

    Returns:
        { "transcript": str, "language": str, "duration_s": float, "latency_ms": int }
    """
    t0 = time.perf_counter()

    # ── Validate file extension ──────────────────────────────────────────────
    filename = file.filename or "audio.webm"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext}'. Supported: {', '.join(sorted(ALLOWED_AUDIO_EXTS))}"
        )

    # ── Read & validate size ─────────────────────────────────────────────────
    audio_bytes = await file.read()
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > MAX_AUDIO_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Audio too large ({size_mb:.1f} MB). Max: {MAX_AUDIO_SIZE_MB} MB"
        )

    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file is empty or too short")

    # ── Save to temp file (faster-whisper reads from file path) ─────────────
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # ── Load model & transcribe ──────────────────────────────────────────
        model = await _get_whisper_model()

        from app.core.config import settings
        language = settings.WHISPER_LANGUAGE  # 'en' by default

        # Run transcription in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(
                tmp_path,
                language=language if language != 'auto' else None,
                vad_filter=True,        # Voice Activity Detection — cuts silence
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
                beam_size=5,
                best_of=5,
                condition_on_previous_text=False,
            )
        )

        # Collect all segment texts
        transcript_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        transcript = " ".join(transcript_parts)

        latency_ms = round((time.perf_counter() - t0) * 1000)
        duration_s = round(info.duration, 2) if hasattr(info, 'duration') else 0.0
        detected_lang = info.language if hasattr(info, 'language') else language

        logger.info(
            f"[STT] User {current_user.id} | lang={detected_lang} | "
            f"duration={duration_s}s | latency={latency_ms}ms | "
            f"transcript_words={len(transcript.split())}"
        )

        if not transcript:
            return JSONResponse({
                "transcript": "",
                "language": detected_lang,
                "duration_s": duration_s,
                "latency_ms": latency_ms,
                "note": "No speech detected in the audio"
            })

        return JSONResponse({
            "transcript": transcript,
            "language": detected_lang,
            "duration_s": duration_s,
            "latency_ms": latency_ms,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Always clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@router.get("/status")
async def voice_status(current_user: User = Depends(get_current_user)):
    """Check if faster-whisper is available and model is loaded."""
    try:
        import faster_whisper
        from app.core.config import settings
        return {
            "available": True,
            "model": settings.WHISPER_MODEL,
            "loaded": _whisper_model is not None,
            "message": "faster-whisper STT is ready"
        }
    except ImportError:
        return {
            "available": False,
            "model": None,
            "loaded": False,
            "message": "faster-whisper not installed. Run: pip install faster-whisper"
        }
