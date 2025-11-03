from coingecko_sdk import AsyncCoingecko
from uuid import uuid4
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

from models.a2a import (
    A2AMessage, TaskResult, TaskStatus, Artifact,
    MessagePart
)
from llm.llm_service import LLMService


class CryptoAgent:
    """
    Handles all cryptocurrency-related operations such as:
    - Fetching coin prices
    - Market data and rankings
    - Historical data and charts
    - Coin metadata and tickers
    - Categories and trending coins
    Each result is passed through an LLM to provide a conversational response.
    """

    def __init__(self, demo_api_key=None, pro_api_key=None, environment="demo", groq_api_key=None):
        # Initialize CoinGecko client
        if environment == "pro" and pro_api_key:
            self.client = AsyncCoingecko(pro_api_key=pro_api_key, environment="pro")
        elif environment == "demo" and demo_api_key:
            self.client = AsyncCoingecko(demo_api_key=demo_api_key, environment="demo")
        else:
            self.client = AsyncCoingecko()

        # Initialize LLM service
        self.llm = LLMService(api_key=groq_api_key)

        # Context tracking
        self.price_history: Dict[str, list] = {}
        self.conversation_history: Dict[str, list] = {}

   
    # message handler
    
    async def process_messages(self, messages: List[A2AMessage], context_id=None, task_id=None, config=None) -> TaskResult:
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())
        user_message = messages[-1] if messages else None
        if not user_message:
            raise ValueError("No message provided")

        message_text = self._extract_message_text(user_message)
        print(f"Processing user query: '{message_text}'")

        # Analyze user intent with LLM
        intent_data = await self.llm.analyze_intent(message_text, context_id)
        print(f"Intent detected: {intent_data}")

        # Only ask for clarification if we truly need more info AND there's no coin_id
        intent = intent_data.get("intent", "get_price")
        coin_id = intent_data.get("coin_id")
        needs_info = intent_data.get("needs_info", False)
        
        # only clarify if no coin AND intent requires a coin
        requires_coin = intent in ["get_price", "coin_info", "historical_data"]
        if needs_info and requires_coin and not coin_id:
            return self._create_clarification_response(messages, context_id, task_id)

        # Route to appropriate handler
        if intent == "get_price":
            return await self._handle_price_query(messages, context_id, task_id, intent_data, message_text)
        elif intent == "compare_prices":
            return await self._handle_comparison(messages, context_id, task_id, intent_data, message_text)
        elif intent == "market_data":
            return await self._handle_market_data(messages, context_id, task_id, intent_data, message_text)
        elif intent == "coin_info":
            return await self._handle_coin_info(messages, context_id, task_id, intent_data, message_text)
        elif intent == "historical_data":
            return await self._handle_historical_data(messages, context_id, task_id, intent_data, message_text)
        elif intent == "categories":
            return await self._handle_categories(messages, context_id, task_id, intent_data, message_text)
        elif intent == "general_question":
            return await self._handle_general_question(messages, context_id, task_id, message_text)
        else:
            return self._create_clarification_response(messages, context_id, task_id)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _extract_message_text(self, user_message: A2AMessage) -> str:
        """Extracts plain text from A2AMessage parts."""
        for part in user_message.parts:
            if part.kind == "text" and part.text:
                return re.sub(r"<[^>]+>", "", part.text.strip())
        raise ValueError("No valid text found in message.")

    async def _compose_llm_response(self, user_query: str, data_summary: str, context: str = "") -> str:
        """
        Passes the factual data through the LLM to create a natural, conversational response.
        """
        prompt = (
            f"User asked: '{user_query}'.\n"
            f"Here is the factual data retrieved:\n{data_summary}\n\n"
            f"Context: {context}\n"
            f"Now respond conversationally — be clear, factual, and helpful. "
            f"If possible, include relevant insights or advice."
        )
        return await self.llm.generate(prompt)

    
    # CoinGecko API Methods 
    
    
    async def get_price(self, coin_id: str, currency: str = "usd") -> Optional[float]:
        """Fetch live price from CoinGecko API."""
        try:
            data = await self.client.simple.price.get(vs_currencies=currency, ids=coin_id)
            if coin_id in data and hasattr(data[coin_id], currency):
                return getattr(data[coin_id], currency)
        except Exception as e:
            print(f"Error fetching price: {e}")
        return None

    async def get_supported_currencies(self) -> Optional[List[str]]:
        """Query all supported currencies on CoinGecko."""
        try:
            currencies = await self.client.simple.supported_vs_currencies.get()
            return list(currencies) if currencies else None
        except Exception as e:
            print(f"Error fetching supported currencies: {e}")
        return None

    async def get_coins_list(self, include_platform: bool = False) -> Optional[List[Dict]]:
        """Query all supported coins with ID, name, and symbol."""
        try:
            coins = await self.client.coins.list.get(include_platform=include_platform)
            return [{"id": c.id, "symbol": c.symbol, "name": c.name} for c in coins] if coins else None
        except Exception as e:
            print(f"Error fetching coins list: {e}")
        return None

    async def get_markets(self, currency: str = "usd", per_page: int = 10, page: int = 1, 
                         order: str = "market_cap_desc") -> Optional[List[Dict]]:
        """Query coins with price, market cap, volume, and market data."""
        try:
            markets = await self.client.coins.markets.get(
                vs_currency=currency,
                per_page=per_page,
                page=page,
                order=order
            )
            if not markets:
                return None
            
            return [{
                "id": m.id,
                "symbol": m.symbol,
                "name": m.name,
                "current_price": getattr(m, 'current_price', None),
                "market_cap": getattr(m, 'market_cap', None),
                "total_volume": getattr(m, 'total_volume', None),
                "price_change_24h": getattr(m, 'price_change_24h', None),
                "price_change_percentage_24h": getattr(m, 'price_change_percentage_24h', None),
                "market_cap_rank": getattr(m, 'market_cap_rank', None)
            } for m in markets]
        except Exception as e:
            print(f"Error fetching markets: {e}")
        return None

    async def get_coin_details(self, coin_id: str, localization: bool = False, 
                              tickers: bool = False, market_data: bool = True) -> Optional[Dict]:
        """Query all metadata for a coin (image, websites, description, etc.)."""
        try:
            coin = await self.client.coins.get(
                id=coin_id,
                localization=localization,
                tickers=tickers,
                market_data=market_data
            )
            if not coin:
                return None
            
            return {
                "id": coin.id,
                "symbol": getattr(coin, 'symbol', None),
                "name": getattr(coin, 'name', None),
                "description": getattr(coin, 'description', {}).get('en', '') if hasattr(coin, 'description') else '',
                "image": getattr(coin, 'image', {}).__dict__ if hasattr(coin, 'image') else {},
                "market_cap_rank": getattr(coin, 'market_cap_rank', None),
                "links": getattr(coin, 'links', {}).__dict__ if hasattr(coin, 'links') else {},
                "market_data": getattr(coin, 'market_data', {}).__dict__ if hasattr(coin, 'market_data') else {}
            }
        except Exception as e:
            print(f"Error fetching coin details: {e}")
        return None

    async def get_coin_tickers(self, coin_id: str, exchange_ids: str = None, 
                              page: int = 1) -> Optional[Dict]:
        """Query coin tickers on both CEX and DEX."""
        try:
            tickers = await self.client.coins.tickers.get(
                id=coin_id,
                exchange_ids=exchange_ids,
                page=page
            )
            if not tickers:
                return None
            
            return {
                "name": getattr(tickers, 'name', None),
                "tickers": [
                    {
                        "base": t.base,
                        "target": t.target,
                        "market": getattr(t, 'market', {}).name if hasattr(t, 'market') else None,
                        "last": getattr(t, 'last', None),
                        "volume": getattr(t, 'volume', None)
                    } for t in getattr(tickers, 'tickers', [])
                ]
            }
        except Exception as e:
            print(f"Error fetching tickers: {e}")
        return None

    async def get_coin_history(self, coin_id: str, date: str) -> Optional[Dict]:
        """Query historical data at a given date (format: DD-MM-YYYY)."""
        try:
            history = await self.client.coins.history.get(id=coin_id, date=date)
            if not history:
                return None
            
            return {
                "id": history.id,
                "symbol": getattr(history, 'symbol', None),
                "name": getattr(history, 'name', None),
                "market_data": getattr(history, 'market_data', {}).__dict__ if hasattr(history, 'market_data') else {}
            }
        except Exception as e:
            print(f"Error fetching coin history: {e}")
        return None

    async def get_market_chart(self, coin_id: str, currency: str = "usd", 
                              days: str = "7") -> Optional[Dict]:
        """Get historical chart data (price, market cap, volume)."""
        try:
            chart = await self.client.coins.market_chart.get(
                id=coin_id,
                vs_currency=currency,
                days=days
            )
            if not chart:
                return None
            
            return {
                "prices": getattr(chart, 'prices', []),
                "market_caps": getattr(chart, 'market_caps', []),
                "total_volumes": getattr(chart, 'total_volumes', [])
            }
        except Exception as e:
            print(f"Error fetching market chart: {e}")
        return None

    async def get_market_chart_range(self, coin_id: str, currency: str = "usd", 
                                    from_timestamp: int = None, to_timestamp: int = None) -> Optional[Dict]:
        """Get historical chart data within a time range (UNIX timestamps)."""
        try:
            chart = await self.client.coins.market_chart_range.get(
                id=coin_id,
                vs_currency=currency,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            )
            if not chart:
                return None
            
            return {
                "prices": getattr(chart, 'prices', []),
                "market_caps": getattr(chart, 'market_caps', []),
                "total_volumes": getattr(chart, 'total_volumes', [])
            }
        except Exception as e:
            print(f"Error fetching market chart range: {e}")
        return None

    async def get_ohlc(self, coin_id: str, currency: str = "usd", days: str = "7") -> Optional[List]:
        """Get OHLC chart data (Open, High, Low, Close)."""
        try:
            ohlc = await self.client.coins.ohlc.get(
                id=coin_id,
                vs_currency=currency,
                days=days
            )
            return list(ohlc) if ohlc else None
        except Exception as e:
            print(f"Error fetching OHLC: {e}")
        return None

    async def get_categories_list(self) -> Optional[List[Dict]]:
        """Query all coin categories."""
        try:
            categories = await self.client.coins.categories.list.get()
            return [{"id": c.category_id, "name": c.name} for c in categories] if categories else None
        except Exception as e:
            print(f"Error fetching categories list: {e}")
        return None

    async def get_categories(self, order: str = "market_cap_desc") -> Optional[List[Dict]]:
        """Query all categories with market data."""
        try:
            categories = await self.client.coins.categories.get(order=order)
            if not categories:
                return None
            
            return [{
                "id": c.id,
                "name": c.name,
                "market_cap": getattr(c, 'market_cap', None),
                "volume_24h": getattr(c, 'volume_24h', None),
                "market_cap_change_24h": getattr(c, 'market_cap_change_24h', None)
            } for c in categories]
        except Exception as e:
            print(f"Error fetching categories: {e}")
        return None

    async def get_coin_trend(self, coin_id: str, currency: str = "usd") -> Optional[Dict]:
        """Get current trend data including price and 24h change for a specific coin."""
        try:
            # Use markets endpoint to get trend data
            markets = await self.get_markets(currency=currency, per_page=250)
            if not markets:
                return None
            
            # Find the specific coin
            coin_data = next((m for m in markets if m['id'] == coin_id), None)
            return coin_data
        except Exception as e:
            print(f"Error fetching coin trend: {e}")
        return None

    
    # Intent Handlers
    
    
    async def _handle_price_query(self, messages, context_id, task_id, intent_data, original_message):
        coin_id = intent_data.get("coin_id")
        currency = intent_data.get("currency", "usd")

        try:
            price = await self.get_price(coin_id, currency)
            if price is None:
                raise ValueError(f"No price data available for {coin_id}")

            self.price_history.setdefault(context_id, []).append({
                "coin": coin_id, "currency": currency, "price": price
            })

            data_summary = f"Coin: {coin_id}\nCurrency: {currency.upper()}\nPrice: {price:,.2f}"
            response_text = await self._compose_llm_response(original_message, data_summary)

            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id
            )

            artifacts = [
                Artifact(
                    name="price_data", 
                    parts=[
                        MessagePart(kind="text", text=response_text),
                        MessagePart(
                            kind="data", 
                            data={
                                "coin": coin_id,
                                "currency": currency,
                                "price": price
                            }
                        )
                    ]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed"),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            return self._error_result(messages, context_id, task_id, f"Error fetching price: {str(e)}")

    async def _handle_comparison(self, messages, context_id, task_id, intent_data, original_message):
        coin_ids = intent_data.get("coin_ids", [])
        currency = intent_data.get("currency", "usd")

        try:
            prices = {}
            for coin in coin_ids:
                p = await self.get_price(coin, currency)
                if p:
                    prices[coin] = p

            if not prices:
                raise ValueError("No valid price data for comparison.")

            summary_lines = [f"{coin}: {currency.upper()} {price:,.2f}" for coin, price in prices.items()]
            data_summary = "\n".join(summary_lines)
            response_text = await self._compose_llm_response(original_message, data_summary)

            response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=response_text)], taskId=task_id)
            artifacts = [Artifact(name="comparison", parts=[MessagePart(kind="data", data=prices)])]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed"),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            return self._error_result(messages, context_id, task_id, f"Error comparing prices: {str(e)}")

    async def _handle_market_data(self, messages, context_id, task_id, intent_data, original_message):
        """Handle requests for market data and rankings."""
        try:
            per_page = intent_data.get("limit", 10)
            currency = intent_data.get("currency", "usd")
            
            markets = await self.get_markets(currency=currency, per_page=per_page)
            if not markets:
                raise ValueError("No market data available")

            data_summary = "Top Cryptocurrencies by Market Cap:\n"
            for m in markets[:10]:
                data_summary += f"{m['name']} ({m['symbol'].upper()}): {currency.upper()} {m['current_price']:,.2f} | Market Cap: ${m['market_cap']:,.0f}\n"

            response_text = await self._compose_llm_response(original_message, data_summary)
            response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=response_text)], taskId=task_id)
            
            artifacts = [
                Artifact(
                    name="market_data", 
                    parts=[
                        MessagePart(kind="text", text=response_text),
                        MessagePart(kind="data", data=markets)
                    ]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed"),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            return self._error_result(messages, context_id, task_id, f"Error fetching market data: {str(e)}")

    async def _handle_coin_info(self, messages, context_id, task_id, intent_data, original_message):
        """Handle requests for detailed coin information."""
        coin_id = intent_data.get("coin_id")
        
        try:
            details = await self.get_coin_details(coin_id)
            if not details:
                raise ValueError(f"No details available for {coin_id}")

            data_summary = f"Coin: {details['name']} ({details['symbol'].upper()})\n"
            data_summary += f"Rank: #{details['market_cap_rank']}\n"
            
            # Add description snippet
            desc = details.get('description', '')[:300]
            if desc:
                data_summary += f"Description: {desc}...\n"

            response_text = await self._compose_llm_response(original_message, data_summary)
            response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=response_text)], taskId=task_id)
            
            artifacts = [
                Artifact(
                    name="coin_info", 
                    parts=[
                        MessagePart(kind="text", text=response_text),
                        MessagePart(kind="data", data=details)
                    ]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed"),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            return self._error_result(messages, context_id, task_id, f"Error fetching coin info: {str(e)}")

    async def _handle_historical_data(self, messages, context_id, task_id, intent_data, original_message):
        """Handle requests for historical price data and trends."""
        coin_id = intent_data.get("coin_id")
        days = intent_data.get("days", "1")  # Default to 1 day for trend queries
        currency = intent_data.get("currency", "usd")
        
        try:
            # Get market data for current price and 24h change
            markets = await self.get_markets(currency=currency, per_page=250)
            coin_market_data = None
            if markets:
                coin_market_data = next((m for m in markets if m['id'] == coin_id), None)
            
            # Get historical chart data
            chart_data = await self.get_market_chart(coin_id, currency, days)
            
            if not coin_market_data and not chart_data:
                raise ValueError(f"No data available for {coin_id}")

            data_summary = f"Trend analysis for {coin_id}:\n"
            
            # Add current market data if available
            if coin_market_data:
                data_summary += f"Current Price: {currency.upper()} {coin_market_data['current_price']:,.2f}\n"
                if coin_market_data['price_change_24h']:
                    data_summary += f"24h Change: {currency.upper()} {coin_market_data['price_change_24h']:,.2f}\n"
                if coin_market_data['price_change_percentage_24h']:
                    change_pct = coin_market_data['price_change_percentage_24h']
                    trend_direction = "📈 UP" if change_pct > 0 else "📉 DOWN" if change_pct < 0 else "➡️ STABLE"
                    data_summary += f"24h Change %: {change_pct:.2f}% {trend_direction}\n"
                if coin_market_data['market_cap']:
                    data_summary += f"Market Cap: ${coin_market_data['market_cap']:,.0f}\n"
                if coin_market_data['total_volume']:
                    data_summary += f"24h Volume: ${coin_market_data['total_volume']:,.0f}\n"
            
            # Add historical price data if available
            if chart_data and chart_data.get('prices'):
                prices = chart_data['prices']
                data_summary += f"\nHistorical data ({days} day(s)):\n"
                if len(prices) >= 2:
                    start_price = prices[0][1]
                    end_price = prices[-1][1]
                    price_change = end_price - start_price
                    price_change_pct = (price_change / start_price) * 100
                    data_summary += f"Starting price: {currency.upper()} {start_price:,.2f}\n"
                    data_summary += f"Current price: {currency.upper()} {end_price:,.2f}\n"
                    data_summary += f"Change: {currency.upper()} {price_change:,.2f} ({price_change_pct:+.2f}%)\n"

            response_text = await self._compose_llm_response(original_message, data_summary)
            response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=response_text)], taskId=task_id)
            
            artifacts = [
                Artifact(
                    name="trend_data", 
                    parts=[
                        MessagePart(kind="text", text=response_text),
                        MessagePart(kind="data", data={
                            "market_data": coin_market_data,
                            "chart_data": chart_data
                        })
                    ]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed"),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            return self._error_result(messages, context_id, task_id, f"Error fetching trend data: {str(e)}")

    async def _handle_categories(self, messages, context_id, task_id, intent_data, original_message):
        """Handle requests for cryptocurrency categories."""
        try:
            categories = await self.get_categories()
            if not categories:
                raise ValueError("No categories data available")

            data_summary = "Top Cryptocurrency Categories:\n"
            for cat in categories[:10]:
                data_summary += f"{cat['name']}: Market Cap ${cat['market_cap']:,.0f}\n"

            response_text = await self._compose_llm_response(original_message, data_summary)
            response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=response_text)], taskId=task_id)
            
            artifacts = [
                Artifact(
                    name="categories", 
                    parts=[
                        MessagePart(kind="text", text=response_text),
                        MessagePart(kind="data", data=categories)
                    ]
                )
            ]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state="completed"),
                artifacts=artifacts,
                history=messages + [response_message]
            )

        except Exception as e:
            return self._error_result(messages, context_id, task_id, f"Error fetching categories: {str(e)}")

    async def _handle_general_question(self, messages, context_id, task_id, message_text):
        context = ""
        if context_id in self.price_history:
            recent = self.price_history[context_id][-3:]
            context = ", ".join([f"{p['coin']}: {p['currency'].upper()} {p['price']}" for p in recent])

        response_text = await self._compose_llm_response(message_text, "General crypto knowledge request.", context)
        response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=response_text)], taskId=task_id)

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="completed"),
            artifacts=[],
            history=messages + [response_message]
        )

    
    # Utility Methods
    
    def _create_clarification_response(self, messages, context_id, task_id):
        text = (
            "I couldn't identify a specific cryptocurrency or understand your request. "
            "Please mention a coin like Bitcoin (BTC), Ethereum (ETH), Solana (SOL), etc., "
            "or ask about market data, categories, or historical prices."
        )
        response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=text)], taskId=task_id)
        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="input-required"),
            artifacts=[],
            history=messages + [response_message]
        )

    def _error_result(self, messages, context_id, task_id, error_msg):
        response_message = A2AMessage(role="agent", parts=[MessagePart(kind="text", text=error_msg)], taskId=task_id)
        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="failed"),
            artifacts=[],
            history=messages + [response_message]
        )