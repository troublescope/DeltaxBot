import asyncio
import json
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.utils import logger


class WebhookListener:
    """
    A generic webhook listener that receives payloads, logs them, and returns a success response.
    This version maintains the basic structure, including the /webhook endpoint, logging, and server startup.
    """

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.loop = loop
        self.app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        self.server = None
        self.setup_routes()

    def setup_routes(self):
        """
        Set up the routes for the FastAPI application.
        """
        self.app.post("/webhook")(self.handle_webhook)

    async def handle_webhook(self, request: Request) -> JSONResponse:
        """
        Handle incoming webhook requests by reading the JSON payload, logging it, and returning a success response.
        """
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

        # Log the payload for auditing/debugging purposes.
        self.log_payload(payload)
        return JSONResponse(
            content={"status": "success", "message": "Payload received"}
        )

    def log_payload(self, payload: dict):
        """
        Log the received payload to a file for auditing or debugging purposes.
        """
        with open("payload_logs.txt", "a") as log_file:
            log_file.write(json.dumps(payload) + "\n")
        logger.info("Payload has been logged.")

    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Start the FastAPI server using uvicorn.
        """
        config_uvicorn = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="error",
            access_log=False,
        )
        server = uvicorn.Server(config_uvicorn)
        self.server = server

        if self.loop:
            self.loop.create_task(server.serve())
        else:
            asyncio.create_task(server.serve())
