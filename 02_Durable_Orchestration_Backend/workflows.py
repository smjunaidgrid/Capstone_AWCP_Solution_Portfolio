from datetime import timedelta
from temporalio import activity, workflow
import subprocess

# 1. The Activity: This is the actual work (our Sandbox)
@activity.defn
async def run_codeact_sandbox(code: str) -> dict:
    try:
        process = subprocess.run(
            ["python3", "-c", code],
            capture_output=True, text=True, timeout=5
        )
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "output": process.stdout,
            "error": process.stderr
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# 2. The Workflow: The durable state machine that Temporal remembers forever
@workflow.defn
class AgentGovernanceWorkflow:
    @workflow.run
    async def run(self, code_to_run: str) -> dict:
        # Execute the sandbox activity with a strict 10-second timeout
        result = await workflow.execute_activity(
            run_codeact_sandbox,
            code_to_run,
            start_to_close_timeout=timedelta(seconds=10),
        )
        return result