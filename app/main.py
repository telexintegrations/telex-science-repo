import asyncio
import json
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx

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

@app.get("/integraton/json")
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
            "settings": [
                {
                    "label": "Interval", 
                    "type": "text", 
                    "required": True, 
                    "default": "* * * * *"
                },
                {"label": "Keywords", 
                "type": "text", 
                "required": False, 
                "default": "biochemistry, genetics, biotechnology, medicine"
                }
            ],
            "tick_url": f"{base_url}/tick" 
        }
    }

    async def fetch_and_send_articles(payload: MonitorPayload):
    #"Fetch latest PubMed articles and send notifications to Telex""
        keywords = setting.default.split(", "),
        for setting in payload.settings:
            if setting.label.lower() == "keywords" and setting.default:
                keywords = setting.default

    pubmed_search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={keywords}&retmax=5&sort=pub+date&retmode=json"
    async with httpx.AsyncClient() as client:
        try:
            search_response = await client.get(pubmed_search_url)
            search_json = search_response.json()
            id_list = search_json["esearchresult"].get("idlist", [])

            if not id_list:
                return

            fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(id_list)}&retmode=json"
            fetch_response = await client.get(fetch_url)
            
            for article_id in id_list:
                article = articles.get(article_id, {})
                title = article.get("title", "No title available")
                authors = ", ".join([author["name"] for author in article.get("authors", [])]) if "authors" in article else "Unknown authors"
                message += f"- {title} by {authors}\n"

            notification_payload = {
                "message": message.strip(),
                "username": "PubMed Telex Bot",
                "event_name": "New Articles",
                "status": "success"
            }
            await client.post(
                payload.return_url, json=notification_payload
            )
        except Exception as e:
            print(
                f"Error: {e}"
            )


