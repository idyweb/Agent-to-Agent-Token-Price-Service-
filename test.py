import os
from coingecko_sdk import Coingecko
from dotenv import load_dotenv


load_dotenv()


client = Coingecko(
    #pro_api_key=os.environ.get("COINGECKO_PRO_API_KEY"),
    demo_api_key=os.getenv("COINGECKO_DEMO_API_KEY"), 
    environment="demo", # "pro" to initialize the client with Demo API access
)

price_data = client.simple.price.get(
    vs_currencies="usd",
    ids="bitcoin",
)
print(price_data['bitcoin'].usd)