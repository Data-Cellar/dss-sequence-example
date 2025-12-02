from fastapi import FastAPI
from api.routes import router


app = FastAPI(
    title="Dashboard Mediator API",
    description="Dashboard Mediator that orchestrates connector negotiation and transfer via connectors",
    version="1.0.0",
)


app.include_router(router=router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Dashboard Mediator"
    }
