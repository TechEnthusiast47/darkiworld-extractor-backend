from fastapi import FastAPI, HTTPException
from extractor import extract_video

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "service": "darkiworld-extractor"}

@app.get("/extract/{video_id}")
def extract(video_id: str):
    result = extract_video(video_id)

    if not result or not result.get("url"):
        raise HTTPException(status_code=404, detail="video introuvable")

    return result
