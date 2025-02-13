from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Literal
from pydantic import BaseModel
from devices_types import APIOrderDevice
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Home Automation API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderRequest(BaseModel):
    device: str
    action: Literal["toggle", "activate", "deactivate"]

@app.post("/api/device/order")
async def device_order(order: OrderRequest):
    """Process a device order"""
    success = APIOrderDevice.process_order(order.device, order.action)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Device '{order.device}' not found or invalid action '{order.action}'"
        )
    return {"success": True, "device": order.device, "action": order.action}

def start_api_server():
    """Start the API server"""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
