from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Import schemas, services, and the DB dependency
from ..schemas.account import AccountCreate, AccountOut, AccountUpdate
from ..services import account as account_service
# Placeholder for DB dependency, assuming it provides a database session
from ..db.session import get_db # Define this function in core/db/session.py

router = APIRouter(
    prefix="/accounts", # Assuming router is mounted under /v1 in main.py
    tags=["Accounts"],
)

# ----------------- 1. GET: Retrieve All Accounts -----------------
@router.get("/", response_model=List[AccountOut])
def read_accounts(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of all client accounts.
    Used for the main Accounts dashboard view.
    """
    accounts = account_service.get_accounts(db, skip=skip, limit=limit)
    return accounts

# ----------------- 2. POST: Create New Account -----------------
@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_new_account(
    account: AccountCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new client account based on the 'Create New Account' form data.
    """
    try:
        db_account = account_service.create_account(db=db, account_data=account)
        return db_account
    except Exception as e:
        # General error handling (e.g., Delivery Unit ID not found)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Could not create account: {str(e)}"
        )

# ----------------- 3. GET: Retrieve Single Account -----------------
@router.get("/{account_id}", response_model=AccountOut)
def read_account(
    account_id: int, 
    db: Session = Depends(get_db)
):
    """
    Retrieve details for a single account by ID.
    """
    db_account = account_service.get_account(db, account_id=account_id)
    if db_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return db_account

# ----------------- 4. PUT: Update Account -----------------
@router.put("/{account_id}", response_model=AccountOut)
def update_existing_account(
    account_id: int, 
    account: AccountUpdate, 
    db: Session = Depends(get_db)
):
    """
    Update an existing account's details (full update).
    """
    db_account = account_service.update_account(db, account_id=account_id, account_data=account)
    if db_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return db_account

# ----------------- 5. DELETE: Delete Account -----------------
@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_route(
    account_id: int, 
    db: Session = Depends(get_db)
):
    """
    Delete a specific account.
    """
    success = account_service.delete_account(db, account_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return {"message": "Account deleted successfully"}