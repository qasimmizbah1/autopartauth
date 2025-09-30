from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os
load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM =  os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")

security = HTTPBearer()

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

async def require_buyer(credentials = Depends(security)):
    token = credentials.credentials
    payload = verify_jwt(token)
    if payload.get("role") != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Buyer only"
        )
    return payload


async def require_supplier(credentials = Depends(security)):
    token = credentials.credentials
    payload = verify_jwt(token)
    if payload.get("role") != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supplier only"
        )
    return payload


async def require_login(credentials = Depends(security)):
    token = credentials.credentials
    payload = verify_jwt(token)
    if not payload.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Login required",
        )

    return payload