from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes.accounts import router as accounts_router
from routes.categories import router as categories_router
from routes.dashboard import router as dashboard_router
from routes.salaries import router as salaries_router
from routes.settings import router as settings_router
from routes.transactions import router as transactions_router
from routes.transfers import router as transfers_router
from routes.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
