from uuid import uuid4
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseSettings
from PIL import Image

# Optional: install with `pip install chartocr`
from chartocr import ChartOCR


class Settings(BaseSettings):
    """Application settings loaded from environment or .env."""

    CHART_OCR_MODEL: str = "plotneural/chart-ocr"
    UPLOAD_DIR_CHART: str = "dhi.core/data/chart_uploads/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
UPLOAD_DIR = Path(settings.UPLOAD_DIR_CHART)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# Initialize OCR model
ocr = ChartOCR(model_name=settings.CHART_OCR_MODEL)


def parse_chart(image_path: Path) -> Dict[str, Any]:
    """Parse a chart image and return structured data."""
    result = ocr.parse(str(image_path))

    axis_labels = {
        "x": result.get("x_label", ""),
        "y": result.get("y_label", ""),
    }
    series_list = []
    raw_series = result.get("series", [])
    for idx, series in enumerate(raw_series):
        label = series.get("label") or f"series_{idx+1}"
        points = [
            {"x": float(pt.get("x")), "y": float(pt.get("y"))}
            for pt in series.get("points", [])
            if "x" in pt and "y" in pt
        ]
        series_list.append({"label": label, "points": points})

    return {
        "axis_labels": axis_labels,
        "series": series_list,
    }


@app.post("/chart/parse")
async def chart_parse(chart: UploadFile = File(...)):
    try:
        ext = Path(chart.filename).suffix
        filename = f"{uuid4().hex}{ext}"
        save_path = UPLOAD_DIR / filename
        contents = await chart.read()
        save_path.write_bytes(contents)

        img = Image.open(save_path).convert("RGB")
        img.save(save_path)

        parsed = parse_chart(save_path)
        data = {
            "filename": filename,
            **parsed,
        }
        return {"status": "success", "data": data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("chart.parser:app", host="0.0.0.0", port=8003, reload=True)
