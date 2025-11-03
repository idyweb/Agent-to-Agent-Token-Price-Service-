from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    COINGECKO_DEMO_API_KEY: str = os.getenv("COINGECKO_DEMO_API_KEY", "")
    COINGECKO_PRO_API_KEY: str = os.getenv("COINGECKO_PRO_API_KEY", "")
    COINGECKO_ENVIRONMENT: str = os.getenv("COINGECKO_ENVIRONMENT", "demo")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    PORT = int(os.getenv("PORT", 5001))

settings = Settings()