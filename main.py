# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

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
    crypto_agent = CryptoAgent(
        demo_api_key=os.getenv("COINGECKO_DEMO_API_KEY"),
        pro_api_key=os.getenv("COINGECKO_PRO_API_KEY"),
        environment=os.getenv("COINGECKO_ENVIRONMENT", "demo")
    )
    
    yield
    
    # Shutdown: Cleanup
    if crypto_agent:
        await crypto_agent.cleanup()

app = FastAPI(
    title="Crypto Agent A2A",
    description="A crypto-price agent with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/a2a/price")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for crypto agent"""
    try:
        # Parse request body
        body = await request.json()
        
        # Validate JSON-RPC request
        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc must be '2.0' and id is required"
                    }
                }
            )
        
        rpc_request = JSONRPCRequest(**body)
        
        # Extract messages
        messages = []
        context_id = None
        task_id = None
        config = None
        
        if rpc_request.method == "message/send":
            messages = [rpc_request.params.message]
            config = rpc_request.params.configuration
        elif rpc_request.method == "execute":
            messages = rpc_request.params.messages
            context_id = rpc_request.params.contextId
            task_id = rpc_request.params.taskId
        
        # Process with crypto agent
        result = await crypto_agent.process_messages(
            messages=messages,
            context_id=context_id,
            task_id=task_id,
            config=config
        )
        
        # Build response
        response = JSONRPCResponse(
            id=rpc_request.id,
            result=result
        )
        
        return response.model_dump()
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "crypto"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)