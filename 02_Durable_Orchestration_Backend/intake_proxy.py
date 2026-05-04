from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

# Import Temporal Client and our Workflow
from temporalio.client import Client
from workflows import AgentGovernanceWorkflow

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
    "proxy_status": "Listening on Port 8000 (Temporal Active)"
}

@app.get("/status")
async def get_status():
    return system_state

@app.post("/ingest")
async def ingest_agent_task(task: AgentTask):
    workflow_id = f"AWCP-{task.agent_id}-{uuid.uuid4().hex[:6]}"
    
    try:
        # 1. Connect to Temporal
        client = await Client.connect("localhost:7233")
        
        # 2. Start the durable workflow instead of running local subprocess directly!
        result = await client.execute_workflow(
            AgentGovernanceWorkflow.run,
            task.code_to_run,
            id=workflow_id,
            task_queue="awcp-agent-queue",
        )
        
        # 3. If the sandbox failed, increase the Degraded Workflows count
        if result.get("status") == "failed":
            system_state["degraded_workflows"] += 1
            
        return {
            "workflow_id": workflow_id,
            "status": result.get("status"),
            "logs": result.get("output"),
            "errors": result.get("error")
        }
    except Exception as e:
        system_state["degraded_workflows"] += 1
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)