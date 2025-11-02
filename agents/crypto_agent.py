from coingecko_sdk import AsyncCoingecko
from groq import Groq
from uuid import uuid4
from typing import List, Optional, Dict, Any
import json
import re
import os

from models.a2a import (
    A2AMessage, TaskResult, TaskStatus, Artifact,
    MessagePart, MessageConfiguration
)

class CryptoAgent:
    def __init__(self, demo_api_key: str = None, pro_api_key: str = None, 
                 environment: str = "demo", groq_api_key: str = None):
        """
        Initialize CryptoAgent with AsyncCoingecko SDK and Groq LLM
        
        Args:
            demo_api_key: CoinGecko Demo API key
            pro_api_key: CoinGecko Pro API key
            environment: "demo" or "pro"
            groq_api_key: Groq API key for LLM
        """
        # Initialize AsyncCoingecko client
        if environment == "pro" and pro_api_key:
            self.client = AsyncCoingecko(pro_api_key=pro_api_key, environment="pro")
        elif environment == "demo" and demo_api_key:
            self.client = AsyncCoingecko(demo_api_key=demo_api_key, environment="demo")
        else:
            self.client = AsyncCoingecko()
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
        
        self.price_history = {}
        self.conversation_history = {}

    async def process_messages(
    self,
    messages: List[A2AMessage],
    context_id: Optional[str] = None,
    task_id: Optional[str] = None,
    config: Optional[MessageConfiguration] = None
) -> TaskResult:
        """Process incoming messages using LLM for intent detection"""

        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())

        user_message = messages[-1] if messages else None
        if not user_message:
            raise ValueError("No message provided")

        message_text = None
 
        # Strategy 1: Try to find non-empty text in text parts
        for part in user_message.parts:
            if part.kind == "text" and part.text:
                text = part.text.strip()
                text = re.sub(r'<[^>]+>', '', text)  # Remove HTML
                text = text.strip()
                
                if text:  # Found non-empty text
                    message_text = text
                    print(f"✅ Found text in text part: '{message_text}'")
                    break
        
        # Strategy 2: If no valid text found, look in data parts
        if not message_text:
            print(f"⚠️  No valid text in text parts, checking data parts...")
            
            for part in user_message.parts:
                if part.kind == "data" and part.data:
                    # The data might be a list of message objects
                    if isinstance(part.data, list) and len(part.data) > 0:
                        # Get the LAST item (most recent message)
                        last_item = part.data[-1]
                        
                        if isinstance(last_item, dict) and last_item.get("kind") == "text":
                            text = last_item.get("text", "")
                            text = text.strip()
                            text = re.sub(r'<[^>]+>', '', text)
                            text = text.strip()
                            
                            if text:
                                message_text = text
                                print(f"✅ Found text in data part (last item): '{message_text}'")
                                break
        
        if not message_text:
            raise ValueError("No text content in message")

        print(f"📝 Processing user query: '{message_text}'")

        # Use LLM to understand intent
        if self.groq_client:
            print(f"🤖 Analyzing with LLM...")
            intent_data = await self._analyze_with_llm(message_text, context_id)
            print(f"🎯 Intent: {intent_data.get('intent')}, Coin: {intent_data.get('coin_id')}")
        else:
            coin_id, currency = self._parse_message(message_text)
            intent_data = {
                "intent": "get_price",
                "coin_id": coin_id,
                "currency": currency,
                "needs_info": coin_id is None
            }

        # Handle different intents
        if intent_data.get("needs_info"):
            return self._create_clarification_response(
                messages, context_id, task_id, intent_data
            )

        intent = intent_data.get("intent", "get_price")
        
        if intent == "get_price":
            return await self._handle_price_query(
                messages, context_id, task_id, intent_data, message_text
            )
        elif intent == "compare_prices":
            return await self._handle_comparison(
                messages, context_id, task_id, intent_data, message_text
            )
        elif intent == "general_question":
            return await self._handle_general_question(
                messages, context_id, task_id, message_text
            )
        else:
            return await self._handle_price_query(
                messages, context_id, task_id, intent_data, message_text
            )


    async def _analyze_with_llm(self, message: str, context_id: str) -> Dict[str, Any]:
        """Use Groq LLM to analyze user message and extract intent"""
        
        # Build conversation context
        if context_id not in self.conversation_history:
            self.conversation_history[context_id] = []
        
        # System prompt for the LLM
        system_prompt = """You are a cryptocurrency assistant. Analyze the user's message and extract:
1. intent: 
   - "get_price" for asking about ONE specific coin (even if multiple mentioned, use the LAST one)
   - "compare_prices" ONLY if user explicitly asks to "compare" multiple coins
   - "general_question" for other crypto questions
2. coin_id: CoinGecko ID of the cryptocurrency (for get_price)
3. coin_ids: Array of coin IDs (ONLY for compare_prices)
4. currency: preferred currency (default: usd)
5. needs_info: true if you cannot identify a specific coin

Supported coins:
- bitcoin/btc -> bitcoin
- ethereum/eth -> ethereum  
- solana/sol -> solana
- binance/bnb -> binancecoin
- cardano/ada -> cardano

IMPORTANT RULES:
- If user mentions multiple coins without the word "compare", use "get_price" with the LAST coin mentioned
- Only use "compare_prices" if user explicitly says "compare X and Y" or similar
- Examples:
  * "bitcoin solana bnb" -> {"intent": "get_price", "coin_id": "binancecoin"} (last coin)
  * "what's the price of bnb?" -> {"intent": "get_price", "coin_id": "binancecoin"}
  * "compare bitcoin and solana" -> {"intent": "compare_prices", "coin_ids": ["bitcoin", "solana"]}

Return ONLY a valid JSON object."""

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
            return result
            
        except Exception as e:
            print(f"LLM analysis error: {e}")
            # Fallback to simple parsing
            coin_id, currency = self._parse_message(message)
            return {
                "intent": "get_price",
                "coin_id": coin_id,
                "currency": currency,
                "needs_info": coin_id is None
            }

    async def _handle_price_query(
        self, messages: List[A2AMessage], context_id: str, 
        task_id: str, intent_data: Dict, original_message: str
    ) -> TaskResult:
        """Handle single price query"""
        
        coin_id = intent_data.get("coin_id")
        currency = intent_data.get("currency", "usd")

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

            # Generate natural response with LLM
            if self.groq_client:
                print(f"✨ Generating natural response with LLM")
                response_text = await self._generate_llm_response(
                    original_message, coin_id, price, currency, context_id
                )
            else:
                print(f"📝 Using template response")
                response_text = (
                    f"The current price of {coin_id.title()} is "
                    f"{currency.upper()} {price:,.2f}"
                )

            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id,
                metadata={
                    "method": "llm" if self.groq_client else "fallback",
                    "model": "llama-3.3-70b-versatile" if self.groq_client else None
                }
            )

            artifacts = [
                Artifact(
                    name="price",
                    parts=[MessagePart(kind="text", text=f"{price}")]
                ),
                Artifact(
                    name="coin_info",
                    parts=[MessagePart(
                        kind="text",
                        text=f"Coin: {coin_id}\nCurrency: {currency.upper()}\nPrice: {price:,.2f}"
                    )]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed", message=response_message),
                artifacts=artifacts,
                history=messages + [response_message]
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
                status=TaskStatus(state="failed", message=response_message),
                artifacts=[],
                history=messages + [response_message]
            )

    async def _handle_comparison(
        self, messages: List[A2AMessage], context_id: str, 
        task_id: str, intent_data: Dict, original_message: str
    ) -> TaskResult:
        """Handle comparison of multiple coins"""
        
        coin_ids = intent_data.get("coin_ids", [])
        currency = intent_data.get("currency", "usd")
        
        if not coin_ids or len(coin_ids) < 2:
            coin_ids = self._extract_multiple_coins(original_message)

        try:
            prices = {}
            for coin_id in coin_ids:
                price = await self.get_price(coin_id, currency)
                if price:
                    prices[coin_id] = price

            if not prices:
                raise ValueError("Could not fetch prices for comparison")

            # Generate comparison with LLM
            if self.groq_client:
                response_text = await self._generate_comparison_response(
                    prices, currency, context_id
                )
            else:
                response_text = "Price Comparison:\n"
                for coin, price in prices.items():
                    response_text += f"- {coin.title()}: {currency.upper()} {price:,.2f}\n"

            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id
            )

            artifacts = [
                Artifact(
                    name="comparison",
                    parts=[MessagePart(kind="data", data=prices)]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed", message=response_message),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            response_text = f"Error comparing prices: {str(e)}"
            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id
            )

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed", message=response_message),
                artifacts=[],
                history=messages + [response_message]
            )

    async def _handle_general_question(
        self, messages: List[A2AMessage], context_id: str, 
        task_id: str, message_text: str
    ) -> TaskResult:
        """Handle general cryptocurrency questions"""
        
        if not self.groq_client:
            response_text = "I can help you with cryptocurrency prices. Please ask about a specific coin."
        else:
            try:
                # Get context from price history
                context = ""
                if context_id in self.price_history:
                    recent = self.price_history[context_id][-3:]
                    context = "Recent queries: " + ", ".join([
                        f"{p['coin']}: {p['currency'].upper()} {p['price']}" 
                        for p in recent
                    ])

                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system", 
                            "content": f"You are a helpful cryptocurrency assistant. {context}"
                        },
                        {"role": "user", "content": message_text}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                response_text = response.choices[0].message.content
                
            except Exception as e:
                response_text = f"I'm here to help with crypto prices. What would you like to know?"

        response_message = A2AMessage(
            role="agent",
            parts=[MessagePart(kind="text", text=response_text)],
            taskId=task_id
        )

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="completed", message=response_message),
            artifacts=[],
            history=messages + [response_message]
        )

    async def _generate_llm_response(
        self, original_message: str, coin_id: str, 
        price: float, currency: str, context_id: str
    ) -> str:
        """Generate natural language response using LLM"""
        
        try:
            prompt = f"""User asked: "{original_message}"
            
Coin: {coin_id}
Price: {currency.upper()} {price:,.2f}

Generate a natural, conversational response providing this price information. Be helpful and concise."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful cryptocurrency assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM response generation error: {e}")
            return f"The current price of {coin_id.title()} is {currency.upper()} {price:,.2f}"

    async def _generate_comparison_response(
        self, prices: Dict[str, float], currency: str, context_id: str
    ) -> str:
        """Generate comparison response using LLM"""
        
        try:
            price_list = "\n".join([
                f"- {coin.title()}: {currency.upper()} {price:,.2f}" 
                for coin, price in prices.items()
            ])
            
            prompt = f"""Compare these cryptocurrency prices:
{price_list}

Provide insights about the price differences and any notable observations."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a cryptocurrency market analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Comparison generation error: {e}")
            result = "Price Comparison:\n"
            for coin, price in prices.items():
                result += f"- {coin.title()}: {currency.upper()} {price:,.2f}\n"
            return result

    def _create_clarification_response(
        self, messages: List[A2AMessage], context_id: str, 
        task_id: str, intent_data: Dict
    ) -> TaskResult:
        """Create response asking for clarification"""
        
        response_text = (
            "I couldn't identify a specific cryptocurrency. "
            "I can help you with prices for coins like Bitcoin (BTC), "
            "Ethereum (ETH), Solana (SOL), Cardano (ADA), and many others. "
            "Which coin would you like to know about?"
        )
        
        response_message = A2AMessage(
            role="agent",
            parts=[MessagePart(kind="text", text=response_text)],
            taskId=task_id
        )

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="input-required", message=response_message),
            artifacts=[],
            history=messages + [response_message]
        )

    def _parse_message(self, text: str) -> tuple[Optional[str], str]:
        """Parse message to extract coin ID and currency (fallback method)"""
        text_lower = text.lower()

        coin_map = {
            "bitcoin": "bitcoin", "btc": "bitcoin",
            "ethereum": "ethereum", "eth": "ethereum",
            "solana": "solana", "sol": "solana",
            "cardano": "cardano", "ada": "cardano",
            "ripple": "ripple", "xrp": "ripple",
            "polkadot": "polkadot", "dot": "polkadot",
            "dogecoin": "dogecoin", "doge": "dogecoin",
            "avalanche": "avalanche", "avax": "avalanche",
            "chainlink": "chainlink", "link": "chainlink",
            "polygon": "matic-network", "matic": "matic-network",
            "litecoin": "litecoin", "ltc": "litecoin",
            "binance": "binancecoin", "bnb": "binancecoin",
            "shiba": "shiba-inu", "shib": "shiba-inu",
            "uniswap": "uniswap", "uni": "uniswap",
        }

        coin_id = None
        for key, value in coin_map.items():
            if key in text_lower:
                coin_id = value
                break

        currency = "usd"
        currencies = ["usd", "eur", "gbp", "jpy", "cad", "aud"]
        for curr in currencies:
            if curr in text_lower:
                currency = curr
                break

        return coin_id, currency

    def _extract_multiple_coins(self, text: str) -> List[str]:
        """Extract multiple coin IDs from text"""
        text_lower = text.lower()
        coin_map = {
            "bitcoin": "bitcoin", "btc": "bitcoin",
            "ethereum": "ethereum", "eth": "ethereum",
            "solana": "solana", "sol": "solana",
            "cardano": "cardano", "ada": "cardano",
        }
        
        found_coins = []
        for key, value in coin_map.items():
            if key in text_lower and value not in found_coins:
                found_coins.append(value)
        
        return found_coins

    async def get_price(self, coin_id: str, currency: str = "usd") -> float:
        """Fetch the current price of a coin from CoinGecko"""
        try:
            price_data = await self.client.simple.price.get(
                vs_currencies=currency,
                ids=coin_id,
            )
            
            if coin_id in price_data and hasattr(price_data[coin_id], currency):
                return getattr(price_data[coin_id], currency)
            
            return None
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None

    async def cleanup(self):
        """Cleanup resources"""
        self.price_history.clear()
        self.conversation_history.clear()
        if hasattr(self.client, 'close'):
            await self.client.close()