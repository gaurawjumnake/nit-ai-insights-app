from fastapi import FastAPI
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String
from backend.app.api import account as account_api 
from backend.app.db.base import Base  # Base Class for SQLAlchemy Models
from backend.app.db.session import engine
from backend.app.models import account, delivery_unit, project # Import all models to ensure Base knows about them

# --- TEMPORARY DATABASE SETUP (RUN ONCE) ---
def init_db():
    """
    Creates all tables in the PostgreSQL database based on the SQLAlchemy Base metadata.
    NOTE: Run this function ONCE, then comment out the call below.
    """
    print("Creating database tables...")
    # This will use the engine configured in session.py to connect to Postgres
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
# -------------------------------------------


# --- FASTAPI APPLICATION SETUP ---
app = FastAPI(
    title="AI Insight Platform API",
    version="1.0.0",
    description="API for managing Accounts, Delivery Units, and Projects.",
)

# Mount the account router under the /v1 prefix
app.include_router(account_api.router, prefix="/v1")

# Call the function to initialize tables. 
# init_db()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API is running"}
