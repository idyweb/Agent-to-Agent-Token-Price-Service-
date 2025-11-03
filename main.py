from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import traceback
import uvicorn

from core.config import settings
from core.startup import lifespan
from models.a2a import JSONRPCRequest, JSONRPCResponse


app = FastAPI(
    title="Crypto Agent A2A",
    description="A crypto-price agent with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/a2a/price")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for crypto agent."""
    try:
        body = await request.json()
        request_id = body.get("id")
        method = body.get("method")

        print(f"\n📨 Received {method} request (id={request_id})")

        # Validate JSON-RPC structure
        if body.get("jsonrpc") != "2.0":
            raise ValueError("Invalid Request: jsonrpc must be '2.0'")
        if "id" not in body:
            raise ValueError("Invalid Request: id is required")

        # Parse request
        rpc_request = JSONRPCRequest(**body)
        messages, config, context_id, task_id = [], None, None, None

        # Handle A2A methods
        if rpc_request.method == "message/send":
            if not hasattr(rpc_request.params, "message"):
                raise ValueError("message/send requires 'message' in params")
            messages = [rpc_request.params.message]
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

        print(f"🤖 Processing {len(messages)} message(s) with crypto agent...")
        result = await request.app.state.crypto_agent.process_messages(
            messages=messages,
            context_id=context_id,
            task_id=task_id,
            config=config
        )

        response = JSONRPCResponse(id=rpc_request.id, result=result)
        print("Agent processing complete")

        return response.model_dump()

    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {error_msg}"
                }
            }
        )

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    crypto_agent = getattr(request.app.state, "crypto_agent", None)
    return {
        "status": "healthy",
        "agent": "crypto",
        "crypto_agent_initialized": crypto_agent is not None
    }

@app.get("/")
async def root():
    return {
        "name": "Crypto Agent A2A",
        "version": "1.0.0",
        "endpoints": {
            "a2a": "/a2a/price",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print(f"Starting server on port {settings.PORT}")
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=True)
