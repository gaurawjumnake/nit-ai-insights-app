from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import account as account_api 
from backend.app.api import delivery_unit as delivery_unit_api
from backend.app.api import project as project_api
from backend.app.api import import_data as import_api
# from backend.app.api import data_extractor as sow_extractor_api
from backend.app.api import export_data as export_api
# from backend.doc_insighter.api import sow as sow_api
from backend.app.api import dashboard as dashboard_api
from backend.app.db.base import Base  
from backend.app.db.session import engine
from backend.app.api import pmo_docs as file_list_api
from pathlib import Path
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="AI Insight Platform API",
    version="1.0.0",
    description="API for managing Accounts, Delivery Units, and Projects.",
)

app.include_router(account_api.router, prefix="/v1")
app.include_router(delivery_unit_api.router, prefix="/v1")
app.include_router(project_api.router, prefix="/v1")
app.include_router(import_api.router, prefix="/v1")
app.include_router(dashboard_api.router, prefix="/v1")
# app.include_router(sow_extractor_api.router,  prefix="/v1")
app.include_router(export_api.router, prefix="/v1")
# app.include_router(sow_api.router,  prefix="/v1")

# Define Paths
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
PMO_DIR = BACKEND_DIR / "uploaded_docs" / "app_docs" / "pmo"
REVENUE_DIR = BACKEND_DIR / "uploaded_docs" / "app_docs" / "revenue"

# Create folders
PMO_DIR.mkdir(parents=True, exist_ok=True)
REVENUE_DIR.mkdir(parents=True, exist_ok=True)

# Mount them (This enables the download functionality)
app.mount("/static_pmo", StaticFiles(directory=PMO_DIR), name="static_pmo")
app.mount("/static_revenue", StaticFiles(directory=REVENUE_DIR), name="static_revenue")

# Include the Router
app.include_router(file_list_api.router, prefix="/v1", tags=["Project Documents"])

# Call the function to initialize tables. 
# init_db()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],  
)

# if __name__  == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", reload=True)