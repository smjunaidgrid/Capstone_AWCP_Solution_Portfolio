import sys
from pathlib import Path
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

# --- NEW: THE DS BRIDGE ---
# We tell Python to look in our sibling DS folder so we can import the ML tools
ds_path = Path(__file__).resolve().parent.parent / "01_Cognitive_Shield_DS"
sys.path.append(str(ds_path))

# Now we can import the Cognitive Shield bridge you just showed me!
from backend_bridge import build_assessment_from_backend_signal
# --------------------------

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
    "proxy_status": "Listening (DS Cognitive Shield ACTIVE)",
    "latest_assessment": "Waiting for agent activity..."  # Assessment Line
}

s3_client = boto3.client(
    's3',
    endpoint_url='http://127.0.0.1:9000',
    aws_access_key_id='admin',
    aws_secret_access_key='password',
    region_name='us-east-1'
)

try:
    s3_client.head_bucket(Bucket='awcp-ledger')
except:
    s3_client.create_bucket(Bucket='awcp-ledger')

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
        
        # --- NEW: THE COGNITIVE SHIELD EVALUATION ---
        print("3. Workflow Complete! Running Cognitive Shield Assessment...")
        
        # We pass the raw Temporal output into your DS engine!
        assessment = build_assessment_from_backend_signal(
            workflow_identity=workflow_id,
            agent_id=task.agent_id,
            runtime_type=task.runtime_type,
            code_to_run=task.code_to_run,
            idempotency_key=task.idempotency_key,
            sandbox_result=result
        )
        
        print("4. Writing DS Assessment to Evidence Ledger...")
        # Save the receipt as a JSON file in the MinIO bucket
        s3_client.put_object(
            Bucket='awcp-ledger',
            Key=f"{workflow_id}_assessment.json",
            Body=json.dumps(assessment, indent=2)
        )
        print("5. Evidence securely stored.")
        
        system_state["latest_assessment"] = assessment["replay_summary"]["summary"]
        # ------------------------------------------
        
        if result.get("status") == "failed":
            system_state["degraded_workflows"] += 1
            
        return {
            "workflow_id": workflow_id,
            "status": result.get("status"),
            "ds_replay_summary": assessment["replay_summary"]["summary"]
        }
    except Exception as e:
        print(f"!!! ERROR: {str(e)} !!!")
        system_state["degraded_workflows"] += 1
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)