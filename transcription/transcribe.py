from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseSettings
import whisper
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).resolve().parents[1] / '.env')

class Settings(BaseSettings):
    WHISPER_MODEL: str = 'base'
    UPLOAD_DIR_AUDIO: str = 'data/audio_uploads/'

settings = Settings()

UPLOAD_DIR = Path(__file__).resolve().parents[1] / settings.UPLOAD_DIR_AUDIO
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Load whisper model
model = whisper.load_model(settings.WHISPER_MODEL)

app = FastAPI()


def transcribe_audio_file(path: str) -> list[dict]:
    """Transcribe an audio file and return segment dictionaries."""
    result = model.transcribe(str(path))
    return [
        {
            "id": seg.get("id"),
            "start": seg.get("start"),
            "end": seg.get("end"),
            "text": seg.get("text", "").strip(),
        }
        for seg in result.get("segments", [])
    ]

@app.post('/transcribe')
async def transcribe_audio(audio: UploadFile = File(...)):
    # Validate content type
    if audio.content_type not in ['audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/mp3', 'audio/x-m4a', 'audio/mp4', 'audio/x-mpeg-3', 'audio/mpeg3', 'audio/x-mp3']:
        raise HTTPException(status_code=400, detail='Unsupported file type')

    suffix = Path(audio.filename).suffix
    filename = f"{uuid4()}{suffix}"
    file_path = UPLOAD_DIR / filename

    try:
        contents = await audio.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to save file: {e}')

    try:
        segments = transcribe_audio_file(str(file_path))
        response = {
            'status': 'success',
            'filename': filename,
            'transcript': segments,
        }
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Transcription failed: {e}')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("transcription.transcribe:app", host="0.0.0.0", port=8001, reload=True)
