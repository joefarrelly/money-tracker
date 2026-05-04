import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, init_db
from routes.accounts import router as accounts_router
from routes.categories import router as categories_router
from routes.dashboard import router as dashboard_router
from routes.email_imports import router as email_imports_router
from routes.salaries import router as salaries_router
from routes.settings import router as settings_router
from routes.transactions import router as transactions_router
from routes.transfers import router as transfers_router
from routes.upload import router as upload_router

logger = logging.getLogger(__name__)

EMAIL_POLL_INTERVAL = 300  # 5 minutes


async def _poll_loop():
    await asyncio.sleep(5)
    while True:
        try:
            db = SessionLocal()
            try:
                from services.email_poller import poll_emails
                count = await asyncio.to_thread(poll_emails, db)
                if count:
                    logger.info("Email poller: %d new import(s)", count)
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Email poll error: %s", exc)
        await asyncio.sleep(EMAIL_POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_poll_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Money Tracker API",
    description="Personal finance tracker — bank statements, salaries, recurring expenses.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router, prefix="/api/accounts", tags=["accounts"])
app.include_router(categories_router, prefix="/api/categories", tags=["categories"])
app.include_router(transactions_router, prefix="/api/transactions", tags=["transactions"])
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
app.include_router(salaries_router, prefix="/api/salaries", tags=["salaries"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(transfers_router, prefix="/api/transfers", tags=["transfers"])
app.include_router(email_imports_router, prefix="/api/email-imports", tags=["email-imports"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
