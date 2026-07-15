from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.company import router as company_router
from src.api.routes.guest import router as guest_router
from src.api.routes.campaign_images import router as campaign_images_router

app = FastAPI(title="AI Social Campaign Manager", version="0.1.2")

app.include_router(company_router)
app.include_router(guest_router)
app.include_router(campaign_images_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "AI Social Campaign Manager API",
        "version": "0.1.2",
        "status": "running",
    }
