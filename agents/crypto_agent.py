# agents/crypto_agent.py
from coingecko_sdk import AsyncCoingecko
from uuid import uuid4
from typing import List, Optional, Dict, Any

from models.a2a import (
    A2AMessage, TaskResult, TaskStatus, Artifact,
    MessagePart, MessageConfiguration
)

class CryptoAgent:
    def __init__(self, demo_api_key: str = None, pro_api_key: str = None, environment: str = "demo"):
        """
        Initialize CryptoAgent with AsyncCoingecko SDK
        
        Args:
            demo_api_key: CoinGecko Demo API key
            pro_api_key: CoinGecko Pro API key
            environment: "demo" or "pro"
        """
        # Initialize AsyncCoingecko client
        if environment == "pro" and pro_api_key:
            self.client = AsyncCoingecko(pro_api_key=pro_api_key, environment="pro")
        elif environment == "demo" and demo_api_key:
            self.client = AsyncCoingecko(demo_api_key=demo_api_key, environment="demo")
        else:
            # Fallback to public API (no key)
            self.client = AsyncCoingecko()
        
        self.price_history = {}  # Store price queries by context_id

    async def process_messages(
        self,
        messages: List[A2AMessage],
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        config: Optional[MessageConfiguration] = None
    ) -> TaskResult:
        """Process incoming messages and fetch crypto prices"""

        # Generate IDs if not provided
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())

        # Extract last user message
        user_message = messages[-1] if messages else None
        if not user_message:
            raise ValueError("No message provided")

        # Extract text from message
        message_text = ""
        for part in user_message.parts:
            if part.kind == "text":
                message_text = part.text.strip()
                break

        # Parse coin and currency from message
        coin_id, currency = self._parse_message(message_text)

        if not coin_id:
            response_text = (
                "I couldn't identify a cryptocurrency in your message. "
                "Please specify a coin like Bitcoin, Ethereum, Solana, etc."
            )
            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id
            )

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(
                    state="input-required",
                    message=response_message
                ),
                artifacts=[],
                history=messages + [response_message]
            )

        # Fetch price from CoinGecko
        try:
            price = await self.get_price(coin_id, currency)
            
            if price is None:
                raise ValueError(f"No price data available for {coin_id}")

            # Store in history
            if context_id not in self.price_history:
                self.price_history[context_id] = []
            self.price_history[context_id].append({
                "coin": coin_id,
                "price": price,
                "currency": currency,
                "timestamp": task_id
            })

            # Build response message
            response_text = (
                f"The current price of {coin_id.title()} is "
                f"{currency.upper()} {price:,.2f}"
            )

            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id
            )

            # Build artifacts
            artifacts = [
                Artifact(
                    name="price",
                    parts=[MessagePart(
                        kind="text",
                        text=f"{price}"
                    )]
                ),
                Artifact(
                    name="coin_info",
                    parts=[MessagePart(
                        kind="text",
                        text=f"Coin: {coin_id}\nCurrency: {currency.upper()}\nPrice: {price:,.2f}"
                    )]
                )
            ]

            # Build history
            history = messages + [response_message]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(
                    state="completed",
                    message=response_message
                ),
                artifacts=artifacts,
                history=history
            )

        except Exception as e:
            response_text = f"Error fetching price for {coin_id}: {str(e)}"
            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id
            )

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(
                    state="failed",
                    message=response_message
                ),
                artifacts=[],
                history=messages + [response_message]
            )

    def _parse_message(self, text: str) -> tuple[Optional[str], str]:
        """Parse message to extract coin ID and currency"""
        text_lower = text.lower()

        # Map common names to CoinGecko IDs
        coin_map = {
            "bitcoin": "bitcoin",
            "btc": "bitcoin",
            "ethereum": "ethereum",
            "eth": "ethereum",
            "solana": "solana",
            "sol": "solana",
            "cardano": "cardano",
            "ada": "cardano",
            "ripple": "ripple",
            "xrp": "ripple",
            "polkadot": "polkadot",
            "dot": "polkadot",
            "dogecoin": "dogecoin",
            "doge": "dogecoin",
            "avalanche": "avalanche",
            "avax": "avalanche",
            "chainlink": "chainlink",
            "link": "chainlink",
            "polygon": "matic-network",
            "matic": "matic-network",
            "litecoin": "litecoin",
            "ltc": "litecoin",
            "binance": "binancecoin",
            "bnb": "binancecoin",
            "shiba": "shiba-inu",
            "shib": "shiba-inu",
            "uniswap": "uniswap",
            "uni": "uniswap",
        }

        # Find coin
        coin_id = None
        for key, value in coin_map.items():
            if key in text_lower:
                coin_id = value
                break

        # Extract currency (default to USD)
        currency = "usd"
        currencies = ["usd", "eur", "gbp", "jpy", "cad", "aud"]
        for curr in currencies:
            if curr in text_lower:
                currency = curr
                break

        return coin_id, currency

    async def get_price(self, coin_id: str, currency: str = "usd") -> float:
        """Fetch the current price of a coin from CoinGecko using AsyncCoingecko SDK"""
        try:
            # Use await with AsyncCoingecko
            price_data = await self.client.simple.price.get(
                vs_currencies=currency,
                ids=coin_id,
            )
            
            # Extract price from response
            if coin_id in price_data and hasattr(price_data[coin_id], currency):
                return getattr(price_data[coin_id], currency)
            
            return None
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None

    async def cleanup(self):
        """Cleanup resources"""
        self.price_history.clear()
        # Close the async client if it has a close method
        if hasattr(self.client, 'close'):
            await self.client.close()