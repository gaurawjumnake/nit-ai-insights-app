import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ==========================================
# 1. CONFIGURATION
# ==========================================
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")

# Microsoft Entra ID Configuration
# The URL to get the public signing keys
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
# The exact issuer string Microsoft sends in the token
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
# The Audience (who the token is for).
# NOTE: If validation fails, try changing this to: f"api://{CLIENT_ID}"
AUDIENCE = CLIENT_ID 

# Initialize the Security Scheme
security = HTTPBearer()

# ==========================================
# 2. CORE AUTHENTICATION (The Bouncer)
# ==========================================
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Microsoft Access Token.
    Returns the user profile + roles if valid.
    """
    token = credentials.credentials
    
    try:
        # A. Fetch Microsoft's Public Keys (Auto-caches keys)
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # B. Verify the Token Signature, Expiry, Audience, and Issuer
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"verify_at_hash": False}
        )
        
        # C. Extract useful info into a clean dictionary
        user_data = {
            "email": payload.get("preferred_username") or payload.get("email"),
            "name": payload.get("name"),
            "id": payload.get("oid"),
            # "roles" is a list inside the token (e.g., ["App.Admin", "App.User"])
            "roles": payload.get("roles", []) 
        }
        
        return user_data

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        print(f"Token Error: {e}") # Helpful for debugging logs
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ==========================================
# 3. ROLE-BASED ACCESS CONTROL (The VIP List)
# ==========================================
class RoleChecker:
    def __init__(self, allowed_roles: list):
        """
        Define which roles are allowed to access a route.
        Example: RoleChecker(["App.Admin"])
        """
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        """
        This runs automatically when used in Depends().
        It first calls get_current_user to verify the token,
        then checks if the user has the required role.
        """
        user_roles = user.get("roles", [])
        
        # Check if the user has ANY of the allowed roles
        # (Intersection of user's roles and allowed roles)
        has_permission = any(role in self.allowed_roles for role in user_roles)
        
        if not has_permission:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Operation not permitted. Required roles: {self.allowed_roles}"
            )
        
        return user