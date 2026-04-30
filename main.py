import asyncio
import httpx
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from camou import scrape_content
from nfce_parser import parse_nfce

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReceiptRequest(BaseModel):
    receiptId: str
    key: str
    projectUrl: str
    maxRetries: int = 3


ERROR_MSG = "Caso o erro persista, favor notificar a área responsável"


async def scrape_and_notify(receipt_id: str, key: str, webhook_url: str, max_retries: int = 3):
    base_url = "https://ww1.receita.fazenda.df.gov.br/DecVisualizador/Nfce/Captcha"
    url = f"{base_url}?Chave={key}"
    print(url)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries}: scrape start")
            content = await scrape_content(url)

            if not content:
                print(f"Attempt {attempt}: no content retrieved")
                if attempt == max_retries:
                    payload = {
                        "receiptId": receipt_id,
                        "data": None,
                        "error": "No content retrieved",
                    }
                else:
                    continue

            elif ERROR_MSG in content:
                print(f"Attempt {attempt}: error message detected in HTML")
                if attempt == max_retries:
                    payload = {
                        "receiptId": receipt_id,
                        "data": None,
                        "error": "SEFAZ error - max retries reached",
                    }
                else:
                    continue

            else:
                print("Scraping successful, parsing content")
                parsed = parse_nfce(content)
                payload = {
                    "receiptId": receipt_id,
                    "data": parsed,
                }
                break

        except Exception as e:
            payload = {
                "receiptId": receipt_id,
                "data": None,
                "error": str(e),
            }
            if attempt == max_retries:
                break

    try:
        print("Calling webhook")
        print(payload)
        httpx.post(f"{webhook_url}/api/nfce/webhook", json=payload, timeout=30.0, headers={"X-API-Key": os.environ["API_KEY"]}, verify=False)
    except Exception as e:
        print(e)


@app.post("/api/nfce/receipt")
def submit_receipt(request: ReceiptRequest):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.create_task(scrape_and_notify(request.receiptId, request.key, request.projectUrl, request.maxRetries))
    return {"status": "processing", "receiptId": request.receiptId}