from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.scan import router as scan_router

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "ChainShield Backend is Running!"}


app.include_router(scan_router)