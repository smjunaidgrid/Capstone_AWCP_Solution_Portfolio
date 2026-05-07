from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import httpx
import boto3
import json
from datetime import datetime
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
    "proxy_status": "Listening on Port 8000 (Fully Armed)"
}

# --- NEW: MinIO Setup ---
# Connect to our local MinIO Docker container
s3_client = boto3.client(
    's3',
    endpoint_url='http://127.0.0.1:9000',
    aws_access_key_id='admin',       # From docker-compose.yaml
    aws_secret_access_key='password', # From docker-compose.yaml
    region_name='us-east-1'
)

# Ensure the "awcp-ledger" bucket exists when the server starts
try:
    s3_client.head_bucket(Bucket='awcp-ledger')
except:
    s3_client.create_bucket(Bucket='awcp-ledger')
# -------------------------

@app.get("/status")
async def get_status():
    return system_state

@app.post("/ingest")
async def ingest_agent_task(task: AgentTask):
    print(f"\n--- NEW REQUEST RECEIVED FROM: {task.agent_id} ---")
    workflow_id = f"AWCP-{task.agent_id}-{uuid.uuid4().hex[:6]}"
    
    try:
        print("1. Asking OPA for permission...")
        async with httpx.AsyncClient() as http_client:
            opa_response = await http_client.post(
                "http://127.0.0.1:8181/v1/data/awcp/governance/allow",
                json={"input": {"agent_id": task.agent_id, "code_to_run": task.code_to_run}},
                timeout=5.0
            )
            
            is_allowed = opa_response.json().get("result", False)
            if not is_allowed:
                system_state["degraded_workflows"] += 1
                return {"status": "BLOCKED_BY_OPA", "reason": "Policy violation detected"}

        print("2. Request APPROVED. Executing Durable Workflow...")
        client = await Client.connect("127.0.0.1:7233")
        result = await client.execute_workflow(
            AgentGovernanceWorkflow.run,
            task.code_to_run,
            id=workflow_id,
            task_queue="awcp-agent-queue",
        )
        
        # --- NEW: Write to Evidence Ledger ---
        print("3. Workflow Complete! Writing receipt to Evidence Ledger...")
        receipt = {
            "workflow_id": workflow_id,
            "agent_id": task.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "code_executed": task.code_to_run,
            "result": result
        }
        
        # Save the receipt as a JSON file in the MinIO bucket
        s3_client.put_object(
            Bucket='awcp-ledger',
            Key=f"{workflow_id}.json",
            Body=json.dumps(receipt, indent=2)
        )
        print("4. Evidence securely stored.")
        # ------------------------------------
        
        if result.get("status") == "failed":
            system_state["degraded_workflows"] += 1
            
        return {
            "workflow_id": workflow_id,
            "status": result.get("status"),
            "logs": result.get("output"),
            "errors": result.get("error")
        }
    except Exception as e:
        print(f"!!! ERROR: {str(e)} !!!")
        system_state["degraded_workflows"] += 1
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)