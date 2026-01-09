import requests

BASE_URL = "https://darkiworld15.com"
API_URL = BASE_URL + "/api/v1/download/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

def extract_video(video_id: str):
    url = API_URL + video_id

    headers = HEADERS.copy()
    headers["Referer"] = BASE_URL + "/download/" + video_id

    r = requests.get(url, headers=headers, timeout=10)

    if r.status_code != 200:
        return None

    data = r.json()

    if "video" not in data:
        return None

    video = data["video"]

    return {
        "url": video.get("lien"),
        "quality": video.get("qual", {}).get("qual"),
        "languages": [l["lang"] for l in video.get("langues", [])]
    }
