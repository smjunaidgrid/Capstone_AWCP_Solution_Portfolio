import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import AgentGovernanceWorkflow, run_codeact_sandbox

async def main():
    # Connect to the Temporal cluster running in our Docker container
    client = await Client.connect("localhost:7233")
    print("Connected to Temporal Cluster successfully!")

    # Start a worker that listens to a specific "Task Queue"
    worker = Worker(
        client,
        task_queue="awcp-agent-queue",
        workflows=[AgentGovernanceWorkflow],
        activities=[run_codeact_sandbox],
    )
    
    print("Worker is listening for agent tasks...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())