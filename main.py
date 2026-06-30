from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import logging

from camou import scrape_content
from nfce_parser import parse_nfce

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    logger.info(f"Starting scrape_and_notify for receipt {receipt_id}")
    logger.info(f"Key to scrape: {key}")

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{max_retries}: scrape start")
            content = await scrape_content(key)

            if not content:
                logger.info(f"Attempt {attempt}: no content retrieved")
                if attempt == max_retries:
                    payload = {
                        "receiptId": receipt_id,
                        "data": None,
                        "error": "No content retrieved",
                    }
                    break
                continue

            elif ERROR_MSG in content:
                logger.info(f"Attempt {attempt}: error message detected in HTML")
                if attempt == max_retries:
                    payload = {
                        "receiptId": receipt_id,
                        "data": None,
                        "error": "SEFAZ error - max retries reached",
                    }
                    break
                continue

            else:
                logger.info("Scraping successful, parsing content")
                parsed = parse_nfce(content)
                if parsed is None:
                    logger.info(f"Attempt {attempt}: parser returned None (unexpected HTML)")
                    if attempt == max_retries:
                        payload = {
                            "receiptId": receipt_id,
                            "data": None,
                            "error": "Parser returned None - unexpected HTML",
                        }
                        break
                    continue
                payload = {
                    "receiptId": receipt_id,
                    "data": parsed,
                }
                break

        except Exception as e:
            logger.error(f"Exception in attempt {attempt}: {str(e)}")
            if attempt == max_retries:
                payload = {
                    "receiptId": receipt_id,
                    "data": None,
                    "error": str(e),
                }
                break
            continue

    try:
        logger.info("Calling webhook with payload: {payload}")
        httpx.post(f"{webhook_url}/api/nfce/webhook", json=payload, timeout=30.0, headers={"X-API-Key": os.environ["API_KEY"]}, verify=False)
    except Exception as e:
        logger.error(f"Error calling webhook: {str(e)}")


@app.post("/api/nfce/receipt")
async def submit_receipt(request: ReceiptRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received request for receipt {request.receiptId}")
    background_tasks.add_task(
        scrape_and_notify, request.receiptId, request.key, request.projectUrl, request.maxRetries
    )
    return {"status": "processing", "receiptId": request.receiptId}