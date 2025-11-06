from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String
from app.api import account as account_api 
from app.api import delivery_unit as delivery_unit_api
from app.api import project as project_api
from app.api import import_data as import_api
from app.db.base import Base  
from app.db.session import engine
from app.models import account, delivery_unit, project 

# def init_db():
#     """
#     Creates all tables in the PostgreSQL database based on the SQLAlchemy Base metadata.
#     NOTE: Run this function ONCE, then comment out the call below.
#     """
#     print("Creating database tables...")
#     Base.metadata.create_all(bind=engine)
#     print("Tables created successfully.")
# # -------------------------------------------

app = FastAPI(
    title="AI Insight Platform API",
    version="1.0.0",
    description="API for managing Accounts, Delivery Units, and Projects.",
)

app.include_router(account_api.router, prefix="/v1")
app.include_router(delivery_unit_api.router, prefix="/v1")
app.include_router(project_api.router, prefix="/v1")
app.include_router(import_api.router, prefix="/v1")

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
