from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseSettings
from uuid import uuid4
from pathlib import Path
from PIL import Image
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
import torch

class Settings(BaseSettings):
    IMAGE_CAPTION_MODEL: str = "nlpconnect/vit-gpt2-image-captioning"
    UPLOAD_DIR_IMAGE: str = "dhi.core/data/image_uploads/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
UPLOAD_DIR = Path(settings.UPLOAD_DIR_IMAGE)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# Load model and related processors
model = VisionEncoderDecoderModel.from_pretrained(settings.IMAGE_CAPTION_MODEL)
processor = ViTImageProcessor.from_pretrained(settings.IMAGE_CAPTION_MODEL)
tokenizer = AutoTokenizer.from_pretrained(settings.IMAGE_CAPTION_MODEL)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

@app.post("/caption")
async def caption_image(image: UploadFile = File(...)):
    try:
        ext = Path(image.filename).suffix
        filename = f"{uuid4().hex}{ext}"
        saved_path = UPLOAD_DIR / filename
        content = await image.read()
        saved_path.write_bytes(content)

        img = Image.open(saved_path).convert("RGB")
        pixel_values = processor(images=img, return_tensors="pt").pixel_values.to(device)
        output_ids = model.generate(pixel_values, num_beams=4, max_length=50)
        caption = tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
        return {
            "status": "success",
            "filename": filename,
            "caption": caption,
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("image.captioner:app", host="0.0.0.0", port=8002, reload=True)
