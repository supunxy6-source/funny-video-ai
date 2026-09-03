import asyncio
import os
import sys
from sqlalchemy import select

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_session_factory
from app.models.script import Script
from app.models.upload import Upload
from app.models.video import Video

async def main():
    async with async_session_factory() as db:
        result = await db.execute(select(Script).order_by(Script.id.desc()).limit(1))
        script = result.scalar_one_or_none()
        print(f"LATEST SCRIPT ID: {script.id if script else 'None'}")
        if script:
            print(f"Script Title: {script.title}")
            print(f"Script Topic: {script.topic_summary}")
            
        result = await db.execute(select(Upload).order_by(Upload.id.desc()).limit(1))
        upload = result.scalar_one_or_none()
        print(f"\nLATEST UPLOAD ID: {upload.id if upload else 'None'}")
        if upload:
            print(f"Upload Title: {upload.title}")
            print(f"Upload Description: {upload.description}")

if __name__ == "__main__":
    asyncio.run(main())
