from sqlalchemy.orm import Session
from typing import List, Optional
import logging

# Import the ORM model and Pydantic schemas
from ..models.account import Account
from ..schemas.account import AccountCreate, AccountUpdate

logging.basicConfig(level=logging.DEBUG)

# --- READ OPERATIONS ---

def get_accounts(db: Session, skip: int = 0, limit: int = 100) -> List[Account]:
    """Retrieve a list of accounts."""
    return db.query(Account).offset(skip).limit(limit).all()

def get_account(db: Session, account_id: int) -> Optional[Account]:
    """Retrieve a single account by ID."""
    return db.query(Account).filter(Account.id == account_id).first()

# --- CREATE OPERATION ---

def create_account(db: Session, account_data: AccountCreate) -> Account:
    """Create a new account record."""
    logging.debug(f"Creating account with data: {account_data}")
    try:
        # Convert Pydantic model to SQLAlchemy model
        db_account = Account(**account_data.model_dump())
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        return db_account
    except Exception as e:
        logging.error(f"Error creating account: {e}")
        raise

# --- UPDATE OPERATION ---

def update_account(db: Session, account_id: int, account_data: AccountUpdate) -> Optional[Account]:
    """Update an existing account by ID."""
    db_account = get_account(db, account_id)
    if db_account:
        # Update only the fields provided in the AccountUpdate schema
        update_data = account_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_account, key, value)
        
        db.commit()
        db.refresh(db_account)
        return db_account
    return None

# --- DELETE OPERATION ---

def delete_account(db: Session, account_id: int) -> bool:
    """Delete an account by ID."""
    db_account = get_account(db, account_id)
    if db_account:
        db.delete(db_account)
        db.commit()
        return True
    return False
