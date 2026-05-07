from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx
from temporalio.client import Client
from workflows import AgentGovernanceWorkflow

app = FastAPI(title="AWCP Intake Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentTask(BaseModel):
    agent_id: str
    runtime_type: str
    code_to_run: str
    idempotency_key: str = str(uuid.uuid4())

system_state = {
    "degraded_workflows": 0,
    "evidence_ledger": "Connected (Local MinIO)",
    "proxy_status": "Listening on Port 8000 (Temporal & OPA Active)"
}

@app.get("/status")
async def get_status():
    return system_state

@app.post("/ingest")
async def ingest_agent_task(task: AgentTask):
    print(f"\n--- NEW REQUEST RECEIVED FROM: {task.agent_id} ---")
    workflow_id = f"AWCP-{task.agent_id}-{uuid.uuid4().hex[:6]}"
    
    try:
        print("1. Asking OPA for permission...")
        # Forced to use 127.0.0.1 and added a 5-second timeout so it can't hang forever!
        async with httpx.AsyncClient() as http_client:
            opa_response = await http_client.post(
                "http://127.0.0.1:8181/v1/data/awcp/governance/allow",
                json={"input": {"agent_id": task.agent_id, "code_to_run": task.code_to_run}},
                timeout=5.0
            )
            
            is_allowed = opa_response.json().get("result", False)
            print(f"2. OPA Decision: Allowed = {is_allowed}")
            
            if not is_allowed:
                system_state["degraded_workflows"] += 1
                print("3. Request BLOCKED. Returning error to agent.")
                return {"status": "BLOCKED_BY_OPA", "reason": "Policy violation detected"}

        print("3. Request APPROVED. Connecting to Temporal...")
        client = await Client.connect("127.0.0.1:7233")
        
        print("4. Executing Durable Workflow...")
        result = await client.execute_workflow(
            AgentGovernanceWorkflow.run,
            task.code_to_run,
            id=workflow_id,
            task_queue="awcp-agent-queue",
        )
        
        if result.get("status") == "failed":
            system_state["degraded_workflows"] += 1
            
        print("5. Workflow Complete!")
        return {
            "workflow_id": workflow_id,
            "status": result.get("status"),
            "logs": result.get("output"),
            "errors": result.get("error")
        }
    except Exception as e:
        print(f"!!! ERROR OCCURRED: {str(e)} !!!")
        system_state["degraded_workflows"] += 1
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)