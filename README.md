# Sonia - Cryptocurrency Price Agent

A production-ready A2A (Agent-to-Agent) protocol compliant cryptocurrency assistant that provides real-time price information for 100+ cryptocurrencies using CoinGecko API and natural language responses powered by Groq LLM.

## Features

- **Real-time Price Queries**: Get current prices for Bitcoin, Ethereum, Solana, and 100+ cryptocurrencies
- **Natural Language Understanding**: Powered by Llama 3.3 70B via Groq for intelligent query parsing
- **Multi-Currency Support**: Prices available in USD, EUR, GBP, JPY, CAD, AUD, and more
- **Price Comparisons**: Compare multiple cryptocurrencies side-by-side
- **A2A Protocol Compliant**: Fully compatible with agent-to-agent communication standards
- **Conversational Interface**: Natural, human-like responses with context awareness
- **Structured Data Output**: JSON artifacts for downstream integration

## 🏗️ Architecture

```
┌─────────────────┐
│   A2A Platform  │
│  (Telex)  │
└────────┬────────┘
         │ JSON-RPC 2.0
         ▼
┌─────────────────┐
│   FastAPI       │
│   Endpoint      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Crypto Agent   │─────▶│  Groq LLM    │
│                 │      │  (Llama 3.3) │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  CoinGecko API  │
│   (Async SDK)   │
└─────────────────┘
```

## Prerequisites

- Python 3.10 or higher
- CoinGecko API key (Demo or Pro)
- Groq API key
- ngrok (for local development with external platforms)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/idyweb/Agent-to-Agent-Token-Price-Service-
cd Agent-to-Agent-Token-Price-Service-
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -e .

or

pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
# CoinGecko API Keys
COINGECKO_DEMO_API_KEY=your_demo_api_key_here
COINGECKO_PRO_API_KEY=your_pro_api_key_here
COINGECKO_ENVIRONMENT=demo

# Groq API Key
GROQ_API_KEY=your_groq_api_key_here

# Server Configuration
PORT=5001
```

**Get API Keys:**
- CoinGecko: https://www.coingecko.com/en/api/pricing
- Groq: https://console.groq.com/keys

### 4. Run the Server

```bash
python main.py
```

The server will start on `http://localhost:5001`

### 5. Expose with ngrok (for platform integration)

```bash
ngrok http 5001
```

Copy the ngrok URL (e.g., `https://6817a6927ca4.ngrok-free.app`) and use it in your workflow configuration.



## 🔧 Configuration

### CoinGecko API

The agent supports both Demo and Pro CoinGecko API tiers:

- **Demo**: 10,000 calls/month, free tier
- **Pro**: Higher limits, commercial use

Set `COINGECKO_ENVIRONMENT` to `demo` or `pro` in your `.env` file.

### Groq LLM

The agent uses Groq's Llama 3.3 70B model for:
- Intent detection (price query vs comparison vs general question)
- Coin identification from natural language
- Natural language response generation
- Price comparison analysis

## 🎯 Usage Examples

### Single Price Query

**User Input:**
```
What's the price of Bitcoin?
```

**Agent Response:**
```json
{
  "status": "completed",
  "message": "The current price of Bitcoin is USD $110,059.00",
  "artifacts": [{
    "name": "price_data",
    "data": {
      "coin": "bitcoin",
      "price": 110059.0,
      "currency": "USD"
    }
  }]
}
```

### Price Comparison

**User Input:**
```
Compare Bitcoin and Ethereum
```

**Agent Response:**
```json
{
  "status": "completed",
  "message": "Bitcoin is trading at $110,059 while Ethereum is at $3,245. Bitcoin's market dominance and limited supply contribute to its higher price...",
  "artifacts": [{
    "name": "comparison",
    "data": {
      "bitcoin": 110059.0,
      "ethereum": 3245.67
    }
  }]
}
```

### Multi-Currency

**User Input:**
```
What's the price of Solana in EUR?
```

**Agent Response:**
```json
{
  "status": "completed",
  "message": "The current price of Solana is EUR €170.34",
  "artifacts": [{
    "name": "price_data",
    "data": {
      "coin": "solana",
      "price": 170.34,
      "currency": "EUR"
    }
  }]
}
```

## 🔌 API Endpoints

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "agent": "crypto",
  "crypto_agent_initialized": true
}
```

### A2A Endpoint

```bash
POST /a2a/price
Content-Type: application/json
```

**Request Body (JSON-RPC 2.0):**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "What's the price of Bitcoin?"
        }
      ]
    },
    "configuration": {
      "blocking": false
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "id": "task-id",
    "contextId": "context-id",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [{
          "kind": "text",
          "text": "The current price of Bitcoin is USD $110,059.00"
        }]
      }
    },
    "artifacts": [...],
    "history": [...]
  }
}
```

## 🌐 Platform Integration

### Workflow Configuration

Use this JSON configuration to integrate with A2A platforms:

```json
{
  "active": true,
  "category": "utilities",
  "description": "Get real-time cryptocurrency prices and market information for Bitcoin, Ethereum, Solana, and 100+ other cryptocurrencies.",
  "id": "sonia",
  "long_description": "Sonia is a cryptocurrency price assistant that provides real-time market data from CoinGecko. Ask about specific coin prices (e.g., 'What's the price of Bitcoin?'), compare multiple cryptocurrencies, or get general crypto market information. Supports major cryptocurrencies including BTC, ETH, SOL, ADA, BNB, and many more. Prices are available in multiple currencies including USD, EUR, GBP, JPY, CAD, and AUD.",
  "name": "Sonia",
  "nodes": [
    {
      "id": "crypto_agent",
      "name": "Crypto Price Agent",
      "parameters": {
        "description": "Fetches real-time cryptocurrency prices using CoinGecko API",
        "capabilities": [
          "get_single_price",
          "compare_prices",
          "answer_crypto_questions"
        ]
      },
      "type": "a2a/generic-a2a-node",
      "typeVersion": 1,
      "url": "https://your-ngrok-url.ngrok-free.app/a2a/price"
    }
  ],
  "short_description": "Real-time cryptocurrency prices and market data",
  "tags": ["crypto", "cryptocurrency", "bitcoin", "ethereum", "prices", "market-data"],
  "version": "1.0.0"
}
```

## 💰 Supported Cryptocurrencies

The agent supports 100+ cryptocurrencies including:

| Cryptocurrency | Aliases | CoinGecko ID |
|---------------|---------|--------------|
| Bitcoin | BTC, Bitcoin | bitcoin |
| Ethereum | ETH, Ethereum | ethereum |
| Solana | SOL, Solana | solana |
| Binance Coin | BNB, Binance | binancecoin |
| Cardano | ADA, Cardano | cardano |
| Ripple | XRP, Ripple | ripple |
| Polkadot | DOT, Polkadot | polkadot |
| Dogecoin | DOGE, Dogecoin | dogecoin |
| Polygon | MATIC, Polygon | matic-network |
| Avalanche | AVAX, Avalanche | avalanche |
| Chainlink | LINK, Chainlink | chainlink |
| Litecoin | LTC, Litecoin | litecoin |
| Uniswap | UNI, Uniswap | uniswap |
| Shiba Inu | SHIB, Shiba | shiba-inu |

## 🛠️ Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --port 5001
```

### Testing Locally

```bash
# Test health endpoint
curl http://localhost:5001/health

# Test A2A endpoint
curl -X POST http://localhost:5001/a2a/price \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-123",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "parts": [{"kind": "text", "text": "What is the price of Bitcoin?"}]
      }
    }
  }'
```

### Logging

The agent provides detailed logging:

```
📨 Received request: method=message/send
✅ Found text in data part (last item): 'what's the price of bitcoin?'
📝 Processing user query: 'what's the price of bitcoin?'
🤖 Analyzing with LLM...
🎯 Intent: get_price, Coin: bitcoin
✅ Agent processing complete
📤 Sending response
```

## 🐛 Troubleshooting

### "No text content in message"

**Problem:** Platform sends empty text parts with conversation history in data parts.

**Solution:** The agent automatically extracts text from data parts. Ensure you're using the latest version.

### "Internal Server Error"

**Problem:** Missing or invalid API keys.

**Solution:** Check your `.env` file and ensure all API keys are valid:
```bash
# Verify environment variables are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GROQ_API_KEY:', bool(os.getenv('GROQ_API_KEY')))"
```

### LLM Response Truncated

**Problem:** Responses end mid-sentence.

**Solution:** The agent uses `max_tokens=800`. Increase if needed in `crypto_agent.py`:
```python
max_tokens=1000  # Increase this value
```

### CoinGecko Rate Limits

**Problem:** "Rate limit exceeded" errors.

**Solution:** 
- Upgrade to CoinGecko Pro tier
- Implement caching (future enhancement)
- Reduce request frequency

## 📊 Rate Limits

| Service | Free Tier | Pro Tier |
|---------|-----------|----------|
| CoinGecko Demo | 10,000 calls/month | 500,000+ calls/month |
| Groq | 14,400 requests/day | Higher limits available |

## 🔐 Security

- All API keys are stored in `.env` (never commit this file)
- Add `.env` to `.gitignore`
- Use environment-specific configurations
- Implement rate limiting for production use
- Use HTTPS in production (ngrok provides this)

## 🚀 Deployment

### Production Considerations

1. **Use a proper hosting service** (not ngrok):
   - Railway.app
   - Render.com
   - Google Cloud Run
   - AWS Lambda

2. **Set up monitoring**:
   - Add application logging
   - Track API usage
   - Monitor error rates

3. **Implement caching**:
   - Cache CoinGecko responses (prices change slowly)
   - Use Redis for distributed caching

4. **Add rate limiting**:
   - Protect against abuse
   - Stay within API limits


## 🙏 Acknowledgments

- **CoinGecko** for cryptocurrency price data
- **Groq** for fast LLM inference
- **A2A Protocol** for agent communication standards

---

Built with ❤️ using FastAPI, CoinGecko, and Groq