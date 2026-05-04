import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

app = FastAPI(title="AWCP Intake Proxy")

# Allow our React UI to talk to this Python server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentTask(BaseModel):
    agent_id: str
    runtime_type: str
    code_to_run: str
    idempotency_key: str = str(uuid.uuid4())

# A temporary memory store to track our system's health
system_state = {
    "degraded_workflows": 0,
    "evidence_ledger": "Connected (Local MinIO)",
    "proxy_status": "Listening on Port 8000"
}

# The UI will call this endpoint every 15 seconds
@app.get("/status")
async def get_status():
    return system_state

@app.post("/ingest")
async def ingest_agent_task(task: AgentTask):
    workflow_id = f"AWCP-{task.agent_id}-{uuid.uuid4().hex[:6]}"
    
    try:
        # CodeAct Sandbox Execution
        process = subprocess.run(
            ["python3", "-c", task.code_to_run],
            capture_output=True, text=True, timeout=5
        )
        
        # If the agent's code fails, we increase the Degraded Workflows count!
        if process.returncode != 0:
            system_state["degraded_workflows"] += 1
            
        return {
            "workflow_id": workflow_id,
            "status": "success" if process.returncode == 0 else "failed",
            "logs": process.stdout,
            "errors": process.stderr
        }
    except Exception as e:
        system_state["degraded_workflows"] += 1
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)