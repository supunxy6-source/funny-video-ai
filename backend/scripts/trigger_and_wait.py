import asyncio
import os
import sys
import time
from sqlalchemy import select

# Ensure we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.tasks.pipeline import run_full_pipeline
from app.db.session import async_session_factory
from app.models.job import Job

async def main():
    print("🚀 Triggering pipeline...")
    res = run_full_pipeline()
    if hasattr(res, "id"):
        pipeline_run_id = str(res.id)
    else:
        pipeline_run_id = str(res)
    print(f"Pipeline started with ID: {pipeline_run_id}")
    
    print("⏳ Waiting for pipeline to complete...")
    
    while True:
        async with async_session_factory() as db:
            result = await db.execute(
                select(Job).where(Job.pipeline_run_id == pipeline_run_id).order_by(Job.step_order)
            )
            jobs = result.scalars().all()
            
            if not jobs:
                print("Waiting for jobs to be created...")
                await asyncio.sleep(5)
                continue
            
            statuses = [j.status for j in jobs]
            step_summary = ", ".join(f"{j.step_name}: {j.status}" for j in jobs)
            print(f"Current step statuses: [{step_summary}]")
            
            if "failed" in statuses:
                print("❌ Pipeline failed!")
                for j in jobs:
                    if j.status == "failed":
                        print(f"Step {j.step_name} failed: {j.error_message}")
                sys.exit(1)
            
            # Check 1: 10 sequential steps all completed (single-video chain)
            if len(jobs) >= 10 and all(s == "completed" for s in statuses):
                print("✅ Pipeline completed successfully!")
                sys.exit(0)
            
            # Check 2: Notification step completed (single run or early skip)
            if any(j.step_name == "notification" and j.status == "completed" for j in jobs):
                print("✅ Pipeline completed successfully!")
                sys.exit(0)

            # Check 3: Batch pipeline completion marker
            if any(j.step_name == "batch_completion" and j.status == "completed" for j in jobs):
                print("✅ Pipeline completed successfully!")
                sys.exit(0)
                     
        await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
