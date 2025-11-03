import json
from groq import Groq


class LLMService:
    """
    Handles all interactions with the Groq LLM.
    Supports:
    - Intent detection
    - Conversational response generation
    """

    def __init__(self, api_key: str = None):
        self.groq_client = Groq(api_key=api_key) if api_key else None

    def _ensure_client(self):
        if not self.groq_client:
            raise ValueError("Groq client not initialized. Provide an API key.")

    
    # Intent Analysis
    
    async def analyze_intent(self, message: str, context_id: str) -> dict:
        """Use LLM to determine user intent and extract entities."""
        self._ensure_client()

        system_prompt = """You are a cryptocurrency assistant. 
Analyze the user's message and return valid JSON with the appropriate intent.

Available intents:
1. "get_price" - User wants current price of a single coin
2. "compare_prices" - User wants to compare multiple coins
3. "market_data" - User wants market rankings, top coins, market overview, volume data
4. "coin_info" - User wants detailed information about a coin (description, links, metadata)
5. "historical_data" - User wants past prices, charts, trends, price history, 24h changes, percentage changes
6. "categories" - User wants info about crypto categories (DeFi, NFT, etc.)
7. "general_question" - General crypto questions not requiring API data

Response format:
{
  "intent": "get_price" | "compare_prices" | "market_data" | "coin_info" | "historical_data" | "categories" | "general_question",
  "coin_id": string | null,
  "coin_ids": [string] | null,
  "currency": string,
  "days": string | null,
  "limit": number | null,
  "needs_info": boolean
}

Rules:
- "trend", "trending", "24h change", "percentage change", "price change", "historical" → use "historical_data" intent
- "top coins", "market cap", "rankings", "volume", "best performing" → use "market_data" intent
- "tell me about", "what is", "information about", "details" → use "coin_info" intent
- "compare", "vs", "versus" → use "compare_prices" intent
- "categories", "DeFi", "NFT", "gaming" → use "categories" intent
- For historical_data, extract days (default "7" if not specified)
- For market_data, extract limit (default 10)
- Default currency is "usd"
- Common coin mappings: bitcoin/btc→bitcoin, ethereum/eth→ethereum, solana/sol→solana, bnb/binancecoin→binancecoin, cardano/ada→cardano
- If coin mentioned but unclear intent, prefer "get_price"
- Set needs_info to true ONLY if absolutely no coin can be identified AND the intent requires a coin
- If coin_id is extracted successfully, ALWAYS set needs_info to false
- For intents like "market_data" or "categories" that don't need a specific coin, set needs_info to false

Examples:
- "what is the trend of bitcoin now?" → {"intent": "historical_data", "coin_id": "bitcoin", "currency": "usd", "days": "1", "needs_info": false}
- "what is the trend of bitcoin?" → {"intent": "historical_data", "coin_id": "bitcoin", "currency": "usd", "days": "1", "needs_info": false}
- "bitcoin trend" → {"intent": "historical_data", "coin_id": "bitcoin", "currency": "usd", "days": "7", "needs_info": false}
- "bitcoin price" → {"intent": "get_price", "coin_id": "bitcoin", "currency": "usd", "needs_info": false}
- "top 10 crypto" → {"intent": "market_data", "limit": 10, "currency": "usd", "needs_info": false}
- "tell me about ethereum" → {"intent": "coin_info", "coin_id": "ethereum", "needs_info": false}
- "bitcoin vs ethereum" → {"intent": "compare_prices", "coin_ids": ["bitcoin", "ethereum"], "currency": "usd", "needs_info": false}
- "what's the trend?" → {"intent": "get_price", "coin_id": null, "currency": "usd", "needs_info": true}
- "show me some prices" → {"intent": "market_data", "currency": "usd", "needs_info": false}
"""

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            
            # Ensure required fields exist
            if "intent" not in result:
                result["intent"] = "get_price"
            if "currency" not in result:
                result["currency"] = "usd"
            if "needs_info" not in result:
                result["needs_info"] = False
            
            print(f"🧠 LLM Intent Analysis: {result}")
            return result

        except Exception as e:
            print(f"❌ LLM intent analysis error: {e}")
            return {
                "intent": "get_price",
                "coin_id": None,
                "currency": "usd",
                "needs_info": True
            }

   
    # Generic Response Generator
   
    async def generate(self, prompt: str) -> str:
        """Unified LLM text generation method."""
        self._ensure_client()

        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful cryptocurrency assistant. Provide clear, concise, and accurate information. Be conversational but professional."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=600
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ LLM generation error: {e}")
            return "Sorry, I encountered an issue generating that response."