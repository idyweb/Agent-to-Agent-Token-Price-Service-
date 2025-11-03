# core/startup.py
from contextlib import asynccontextmanager
from agents.crypto_agent import CryptoAgent
from core.config import settings

@asynccontextmanager
async def lifespan(app):
    """Lifecycle manager for startup and shutdown events."""
    print("Initializing Crypto Agent...")

    # Attach to FastAPI app state
    app.state.crypto_agent = CryptoAgent(
        demo_api_key=settings.COINGECKO_DEMO_API_KEY,
        pro_api_key=settings.COINGECKO_PRO_API_KEY,
        environment=settings.COINGECKO_ENVIRONMENT,
        groq_api_key=settings.GROQ_API_KEY,
    )

    print("Crypto Agent initialized")
    print(f"COINGECKO_DEMO_API_KEY: {'✓' if settings.COINGECKO_DEMO_API_KEY else '✗'}")
    print(f"GROQ_API_KEY: {'✓' if settings.GROQ_API_KEY else '✗'}")

    try:
        yield
    finally:
        print("🛑 Shutting down Crypto Agent...")
        await app.state.crypto_agent.cleanup()
        print("✅ Cleanup complete")
