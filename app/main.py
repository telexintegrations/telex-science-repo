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


class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str

class MonitorPayload(BaseModel):
    channel_id: str
    return_url: str
    settings: List[Setting]

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

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
            "descriptions": {
                "app_name": "telex-science", 
                "app_description": "Fetches latest PubMed articles and sends notifications via Telex.",
                "app_logo": "https://www.shutterstock.com/image-photo/blue-helix-human-dna-structure-260nw-1669326868.jpg",
                "app_url": base_url,
                "background_color": "#FFFFFF"
            },
            "integration_type": "interval",
            "author"
            "settings": [
                {
                    "label": "Interval", 
                    "type": "text", 
                    "required": True, 
                    "default": "* * * * *"
                },
                {
                    "label": "Keywords", 
                    "type": "text", 
                    "required": False, 
                    "default": "biochemistry, genetics, biotechnology, medicine"
                }
            ],
            "target_url": SLACK_WEBHOOK_URL,
            "tick_url": f"{base_url}/tick" 
        }
    }

async def fetch_and_send_articles(payload: MonitorPayload, interval: int):
    """Fetch latest PubMed articles and send notifications to Telex repeatedly."""
    while True:
        keywords = "biochemistry"  # Default keyword
        for setting in payload.settings:
            if setting.label.lower() == "keywords" and setting.default:
                keywords = setting.default.replace(", ", "+").replace(",", "+")

        pubmed_search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={keywords}&retmax=5&sort=pub+date&retmode=json"
        async with httpx.AsyncClient() as client:
            try:
                search_response = await client.get(pubmed_search_url)
                search_json = search_response.json()
                id_list = search_json["esearchresult"].get("idlist", [])

                if not id_list:
                    await asyncio.sleep(interval)
                    continue

                # Fetch article details (titles)
                fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(id_list)}&retmode=json"
                fetch_response = await client.get(fetch_url)
                fetch_json = fetch_response.json()

                # Extract article titles
                articles = []
                for article_id in id_list:
                    article_info = fetch_json.get("result", {}).get(article_id, {})
                    title = article_info.get("title", "No Title Available")
                    articles.append(f"- **{title}** (PubMed ID: {article_id})")

                # Format message
                message = "**Latest PubMed Articles:**\n" + "\n".join(articles)

                # Send notification
                notification_payload = {
                    "message": message,
                    "username": "PubMed Telex Bot",
                    "event_name": "New Articles",
                    "status": "success"
                }
                await client.post(payload.return_url, json=notification_payload)

            except Exception as e:
                print(f"Error: {e}")

        await asyncio.sleep(interval)

@app.post("/tick", status_code=202)
def monitor(payload: MonitorPayload, background_tasks: BackgroundTasks):
    background_tasks.add_task(fetch_and_send_articles, payload)
    return {"status": "success"}
