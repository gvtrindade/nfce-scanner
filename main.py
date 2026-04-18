from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from camou import scrape_content
from nfce_parser import parse_nfce

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


def scrape_and_notify(receipt_id: str, key: str, webhook_url: str):
    base_url = "https://ww1.receita.fazenda.df.gov.br/DecVisualizador/Nfce/Captcha"
    url = f"{base_url}?Chave={key}"

    try:
        print("Webhook called, scrape start")
        content = scrape_content(url)

        if content:
            print("Scraping successfull, parsing content")
            print(content)
            parsed = parse_nfce(content)
            payload = {
                "receiptId": receipt_id,
                "data": parsed,
            }
        else:
            print("Scraping unsuccessfull, sending error payload")
            payload = {
                "receiptId": receipt_id,
                "data": None,
                "error": "No content retrieved",
            }
    except Exception as e:
        payload = {
            "receiptId": receipt_id,
            "data": None,
            "error": str(e),
        }

    try:
        print("Calling webhook")
        print(payload)
        httpx.post(f"{webhook_url}/api/nfce/webhook", json=payload, timeout=30.0, headers={"X-API-Key": "test-key"})
    except Exception as e:
        print(e)


@app.post("/api/nfce/receipt")
def submit_receipt(request: ReceiptRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        scrape_and_notify, request.receiptId, request.key, request.projectUrl
    )
    return {"status": "processing", "receiptId": request.receiptId}
