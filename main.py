from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
import uvicorn
import re

from core.config import settings
from core.startup import lifespan
from models.a2a import JSONRPCRequest, JSONRPCResponse, A2AMessage, MessagePart


app = FastAPI(
    title="Sonia - Crypto Agent",
    description="A crypto-price agent with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/.well-known/a2a.json")
async def a2a_discovery():
    """Official A2A discovery endpoint."""
    base_url = "https://gent-to-gent-oken-rice-ervice--idyweb3947-izxzesc1.leapcell.dev"
    return {
        "protocol": "a2a",
        "version": "1.0",
        "agent": {
            "name": "Sonia",
            "description": "Real-time cryptocurrency prices and market data assistant",
            "version": "1.0.0",
            "capabilities": ["crypto_prices", "market_data", "price_comparison"]
        },
        "endpoints": {
            "message": f"{base_url}/a2a",
            "execute": f"{base_url}/a2a"
        }
    }

def extract_user_message(msg: A2AMessage) -> str:
    """
    Extract the actual user query from  nested message structure.
    The platform sends conversation history in nested data arrays.
    """
    candidates = []
    
    
    for part in msg.parts:
        if part.kind == "text" and part.text:
            text = re.sub(r"<[^>]+>", "", part.text).strip()
            if text and not text.startswith("Fetching") and len(text) > 3:
                candidates.append(text)
        
        
        elif part.kind == "data" and isinstance(part.data, list):
            for item in part.data:
                if isinstance(item, dict) and item.get("kind") == "text":
                    text = item.get("text", "")
                    # Remove HTML tags
                    text = re.sub(r"<[^>]+>", "", text).strip()
                    # Skip status messages and empty strings
                    if text and not text.startswith("Fetching") and len(text) > 3:
                        candidates.append(text)
    
    # Return the LAST valid message (most recent user query)
    if candidates:
        return candidates[-1]
    
    raise ValueError("No valid user message found")

async def handle_a2a_request(request: Request):
    """Unified A2A request handler following official spec."""
    try:
        body = await request.json()
        request_id = body.get("id")
        method = body.get("method")

        print(f"Method: {method}")
        print(f"ID: {request_id}")

        
        if body.get("jsonrpc") != "2.0":
            raise ValueError("Invalid Request: jsonrpc must be '2.0'")
        if "id" not in body:
            raise ValueError("Invalid Request: id is required")

        # Parse request
        rpc_request = JSONRPCRequest(**body)
        messages, config, context_id, task_id = [], None, None, None

        # Handle different A2A methods
        if rpc_request.method == "message/send":
            if not hasattr(rpc_request.params, "message"):
                raise ValueError("message/send requires 'message' in params")
            
            original_msg = rpc_request.params.message
            
            # Extract the actual user query from nested structure
            try:
                user_text = extract_user_message(original_msg)
                print(f"📝 Extracted User Query: '{user_text}'")
                
                # Create a clean message with just the user query
                clean_message = A2AMessage(
                    role=original_msg.role,
                    parts=[MessagePart(kind="text", text=user_text)],
                    messageId=original_msg.messageId,
                    metadata=original_msg.metadata
                )
                messages = [clean_message]
                
            except Exception as e:
                print(f"⚠️ Message extraction failed: {e}")
                messages = [original_msg]
            
            config = getattr(rpc_request.params, "configuration", None)
            
        elif rpc_request.method == "execute":
            if not hasattr(rpc_request.params, "messages"):
                raise ValueError("execute requires 'messages' in params")
            messages = rpc_request.params.messages
            context_id = getattr(rpc_request.params, "contextId", None)
            task_id = getattr(rpc_request.params, "taskId", None)
            
        else:
            raise ValueError(f"Unknown method: {rpc_request.method}")

        if not messages:
            raise ValueError("No messages provided")

        print(f"🤖 Processing with Crypto Agent...")
        
        # Process with crypto agent
        result = await request.app.state.crypto_agent.process_messages(
            messages=messages,
            context_id=context_id,
            task_id=task_id,
            config=config
        )

        # Build response
        response = JSONRPCResponse(id=rpc_request.id, result=result)
        response_dict = response.model_dump(exclude_none=True)
        
        print(f"✅ Response Status: {response_dict.get('result', {}).get('status', {}).get('state')}")
        print(f"{'='*60}\n")
        
        return JSONResponse(
            content=response_dict,
            headers={'Content-Type': 'application/json'}
        )

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")
        traceback.print_exc()
        
        return JSONResponse(
            status_code=200,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {error_msg}"
                }
            }
        )

@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint following official specification."""
    return await handle_a2a_request(request)

# Alternative endpoints for compatibility
@app.post("/a2a/message")
async def a2a_message(request: Request):
    """Alternative A2A endpoint."""
    return await handle_a2a_request(request)

@app.post("/a2a/price")
async def a2a_price(request: Request):
    """Custom A2A endpoint for backward compatibility."""
    return await handle_a2a_request(request)

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    crypto_agent = getattr(request.app.state, "crypto_agent", None)
    return {
        "status": "healthy",
        "agent": "Sonia",
        "version": "1.0.0",
        "crypto_agent_initialized": crypto_agent is not None,
        "endpoints": {
            "primary": "/a2a",
            "alternative": ["/a2a/message", "/a2a/price"],
            "discovery": "/.well-known/a2a.json"
        }
    }

@app.get("/")
async def root():
    return {
        "name": "Sonia - Crypto Agent",
        "version": "1.0.0",
        "protocol": "a2a",
        "endpoints": {
            "primary": "/a2a",
            "alternatives": ["/a2a/message", "/a2a/price"],
            "discovery": "/.well-known/a2a.json",
            "health": "/health"
        }
    }

if __name__ == "__main__":

    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)