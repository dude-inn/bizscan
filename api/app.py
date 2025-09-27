# -*- coding: utf-8 -*-
"""
FastAPI application for Robokassa callbacks
"""
from fastapi import FastAPI
from api.robokassa_callbacks import router as robokassa_router

app = FastAPI(title="BizScan Payments", version="1.0.0")
app.include_router(robokassa_router)



