# scbr/scbr_main.py
from fastapi import FastAPI
from .scbr_app import router

app = FastAPI(title="SCBR Only")
app.include_router(router, prefix="/api", tags=["S-CBR"])
