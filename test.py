# import os
# from coingecko_sdk import Coingecko
# from dotenv import load_dotenv


# load_dotenv()


# client = Coingecko(
#     #pro_api_key=os.environ.get("COINGECKO_PRO_API_KEY"),
#     demo_api_key=os.getenv("COINGECKO_DEMO_API_KEY"), 
#     environment="demo", # "pro" to initialize the client with Demo API access
# )

# price_data = client.simple.price.get(
#     vs_currencies="usd",
#     ids="bitcoin",
# )
# print(price_data['bitcoin'].usd)

import os

from groq import Groq
from dotenv import load_dotenv


load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model="llama-3.3-70b-versatile",
)

print(chat_completion.choices[0].message.content)