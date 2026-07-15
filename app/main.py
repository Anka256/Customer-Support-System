from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.rate_limit import limiter
from app.routes import tickets

app = FastAPI(
    title="Customer Support System",
    description="AI-powered customer support ticket processing pipeline",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(tickets.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
