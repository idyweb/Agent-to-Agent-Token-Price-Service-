# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import traceback

from models.a2a import JSONRPCRequest, JSONRPCResponse, TaskResult, TaskStatus, Artifact, MessagePart, A2AMessage
from agents.crypto_agent import CryptoAgent

load_dotenv()

# Initialize crypto agent
crypto_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global crypto_agent
    
    # Startup: Initialize the crypto agent
    print("🚀 Initializing Crypto Agent...")
    crypto_agent = CryptoAgent(
        demo_api_key=os.getenv("COINGECKO_DEMO_API_KEY"),
        pro_api_key=os.getenv("COINGECKO_PRO_API_KEY"),
        environment=os.getenv("COINGECKO_ENVIRONMENT", "demo"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )
    print("✅ Crypto Agent initialized")
    
    # Verify API keys
    print(f"🔑 COINGECKO_DEMO_API_KEY: {'✓' if os.getenv('COINGECKO_DEMO_API_KEY') else '✗'}")
    print(f"🔑 GROQ_API_KEY: {'✓' if os.getenv('GROQ_API_KEY') else '✗'}")
    
    yield
    
    # Shutdown: Cleanup
    print("🛑 Shutting down Crypto Agent...")
    if crypto_agent:
        await crypto_agent.cleanup()
    print("✅ Cleanup complete")

app = FastAPI(
    title="Crypto Agent A2A",
    description="A crypto-price agent with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/a2a/price")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for crypto agent"""
    body = None
    request_id = None
    
    try:
        # Parse request body
        body = await request.json()
        request_id = body.get("id")
        
        print(f"\n📨 Received request:")
        print(f"   Method: {body.get('method')}")
        print(f"   ID: {request_id}")
        print(f"   Body keys: {list(body.keys())}")
        
        # Validate JSON-RPC request
        if body.get("jsonrpc") != "2.0":
            print("❌ Invalid jsonrpc version")
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc must be '2.0'"
                    }
                }
            )
        
        if "id" not in body:
            print("❌ Missing id field")
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: id is required"
                    }
                }
            )
        
        # Parse into Pydantic model
        try:
            rpc_request = JSONRPCRequest(**body)
        except Exception as e:
            print(f"❌ Failed to parse request: {e}")
            traceback.print_exc()
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": f"Invalid params: {str(e)}"
                    }
                }
            )
        
        # Extract messages based on method
        messages = []
        context_id = None
        task_id = None
        config = None
        
        print(f"   Processing method: {rpc_request.method}")
        
        if rpc_request.method == "message/send":
            if not hasattr(rpc_request.params, 'message'):
                raise ValueError("message/send requires 'message' in params")
            messages = [rpc_request.params.message]
            config = getattr(rpc_request.params, 'configuration', None)
            print(f"   Message text: {messages[0].parts[0].text if messages[0].parts else 'N/A'}")
            
        elif rpc_request.method == "execute":
            if not hasattr(rpc_request.params, 'messages'):
                raise ValueError("execute requires 'messages' in params")
            messages = rpc_request.params.messages
            context_id = getattr(rpc_request.params, 'contextId', None)
            task_id = getattr(rpc_request.params, 'taskId', None)
            print(f"   Messages count: {len(messages)}")
            print(f"   Context ID: {context_id}")
            print(f"   Task ID: {task_id}")
        else:
            raise ValueError(f"Unknown method: {rpc_request.method}")
        
        # Validate we have messages
        if not messages:
            raise ValueError("No messages provided")
        
        print(f"🤖 Processing with crypto agent...")
        
        # Process with crypto agent
        result = await crypto_agent.process_messages(
            messages=messages,
            context_id=context_id,
            task_id=task_id,
            config=config
        )
        
        print(f"✅ Agent processing complete")
        print(f"   Result status: {result.status.state}")
        
        # Build response
        response = JSONRPCResponse(
            id=rpc_request.id,
            result=result
        )
        
        response_dict = response.model_dump()
        print(f"📤 Sending response (truncated): {str(response_dict)[:200]}...")
        
        return response_dict
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Error processing request:")
        print(f"   Error: {error_msg}")
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {error_msg}"
                }
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "crypto",
        "crypto_agent_initialized": crypto_agent is not None
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Crypto Agent A2A",
        "version": "1.0.0",
        "endpoints": {
            "a2a": "/a2a/price",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5001))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)