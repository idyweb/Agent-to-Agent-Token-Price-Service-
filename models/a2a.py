from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import uuid4

class MessagePart(BaseModel):
    kind: Literal["text", "data", "file", "image", "artifact"]  # Added more types
    text: Optional[str] = None
    data: Optional[Union[Dict[str, Any], List[Any], str, int, float, bool]] = None  # Accept any type
    file_url: Optional[str] = None
    url: Optional[str] = None  # Some platforms use 'url' instead of 'file_url'
    mimeType: Optional[str] = None  # Some platforms include mimeType
    name: Optional[str] = None  # Some platforms include name
    
    class Config:
        extra = "allow"  # Allow extra fields

class A2AMessage(BaseModel):
    kind: Literal["message"] = "message"
    role: Literal["user", "agent", "system"]
    parts: List[MessagePart]
    messageId: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    taskId: Optional[str] = None
    contextId: Optional[str] = None  # Added this
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class PushNotificationConfig(BaseModel):
    url: str
    token: Optional[str] = None
    authentication: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class MessageConfiguration(BaseModel):
    blocking: bool = True
    acceptedOutputModes: Optional[List[str]] = ["text/plain", "image/png", "image/svg+xml"]
    pushNotificationConfig: Optional[PushNotificationConfig] = None
    timeout: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class MessageParams(BaseModel):
    message: A2AMessage
    configuration: Optional[MessageConfiguration] = Field(default_factory=MessageConfiguration)
    
    class Config:
        extra = "allow"

class ExecuteParams(BaseModel):
    contextId: Optional[str] = None
    taskId: Optional[str] = None
    messages: List[A2AMessage]
    configuration: Optional[MessageConfiguration] = None
    
    class Config:
        extra = "allow"

class JSONRPCRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    id: str
    method: Literal["message/send", "execute"]
    params: Union[MessageParams, ExecuteParams]
    
    class Config:
        extra = "allow"

class TaskStatus(BaseModel):
    state: Literal["working", "completed", "input-required", "failed", "running", "cancelled"]
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: Optional[A2AMessage] = None
    progress: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class Artifact(BaseModel):
    artifactId: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    name: str
    parts: List[MessagePart]
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class TaskResult(BaseModel):
    id: str
    contextId: Optional[str] = None  # Made optional
    status: TaskStatus
    artifacts: List[Artifact] = []
    history: List[A2AMessage] = []
    kind: Literal["task"] = "task"
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"

class JSONRPCResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str
    result: Optional[TaskResult] = None
    error: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"