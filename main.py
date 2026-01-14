from fastapi import FastAPI
from api.routes import router

"""
Dashboard Mediator Application Entry Point.

This module initializes the FastAPI application, sets up the API routes,
and defines the main entry point for the service.
"""


app = FastAPI(
    title="Dashboard Mediator API",
    description="Dashboard Mediator that orchestrates connector negotiation and transfer via connectors",
    version="1.0.0",
)


app.include_router(router=router, prefix="/api")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: A dictionary indicating the service status and name.
    """
    return {"status": "healthy", "service": "Dashboard Mediator"}
