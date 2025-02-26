import asyncio
import json
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
from dotenv import load_dotenv

load_dotenv("../.env")

TELEX_WEBHOOK_URL = os.getenv("TELEX_WEBHOOK_URL")

class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str

class MonitorPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: List[Setting]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://staging.telex.im", "https://telex.im"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/integration.json")
def get_integration_json(request: Request):
    base_url = str(request.base_url).rstrip("/")
    return {
        "data": {
            "date": {
                "created_at": "2025-02-24",
                "updated_at": "2025-02-24"
            },
            "descriptions": {
                "app_name": "telex-science",
                "app_description": "Fetches latest PubMed articles and sends notifications via Telex.",
                "app_logo": "https://www.shutterstock.com/image-photo/blue-helix-human-dna-structure-260nw-1669326868.jpg",
                "app_url": "https://telex-science-repo.onrender.com",
                "background_color": "#fff"
            },
            "is_active": True,
            "integration_type": "interval",
            "integration_category": "Monitoring & Logging",
            "key_features": [
                "Monitoring",
                "Real time notification"
            ],
            "author": "abu yusuf",
            "settings": [
                {
                    "label": "Interval",
                    "type": "text",
                    "required": True,
                    "default": "60"
                },
                {
                    "label": "keywords",
                    "type": "text",
                    "required": True,
                    "default": "biochemistry, genetics, cancer"
                },
                {
                    "label": "include logs",
                    "type": "checkbox",
                    "required": True,
                    "default": "true"
                }
            ],
            "target_url": TELEX_WEBHOOK_URL, 
            "tick_url": f"{base_url}/tick"
        }
    }

async def fetch_and_send_articles(payload: MonitorPayload, interval: int):
    while True:
        keywords = "biochemistry, genetics, cancer"
        for setting in payload.settings:
            if setting.label.lower() == "keywords" and setting.default:
                keywords = setting.default.replace(", ", "+").replace(",", "+")

        keyword_list = keywords.split("+")

        for keyword in keyword_list:
            pubmed_search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={keyword}&retmax=5&sort=pub+date&retmode=json"
            async with httpx.AsyncClient() as client:
                try:
                    search_response = await client.get(pubmed_search_url)
                    search_json = search_response.json()
                    id_list = search_json["esearchresult"].get("idlist", [])

                    if not id_list:
                      await asyncio.sleep(interval)
                      continue

                    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(id_list)}&retmode=json"
                    fetch_response = await client.get(fetch_url)
                    fetch_json = fetch_response.json()

                    articles = []
                    for article_id in id_list:
                        article_info = fetch_json.get("result", {}).get(article_id, {})
                        title = article_info.get("title", "No Title Available")
                        articles.append(f"- **{title}** (PubMed ID: {article_id})")

                    message = f"Latest PubMed Articles for '{keyword}':\n" + "\n".join(articles)

                    notification_payload = {
                        "message": message,
                        "username": "PubMed Telex Bot",
                        "event_name": "New Articles",
                        "status": "success"
                    }
                    await client.post(payload.return_url, json=notification_payload)

                except Exception as e:
                    print(f"Error fetching articles for '{keyword}': {e}")

        await asyncio.sleep(interval)

@app.post("/tick", status_code=202)
def monitor(payload: MonitorPayload, background_tasks: BackgroundTasks):
    interval = 60 
    for setting in payload.settings:
        if setting.label.lower() == "interval" and setting.default:
            interval = int(setting.default)

    background_tasks.add_task(fetch_and_send_articles, payload, interval)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)