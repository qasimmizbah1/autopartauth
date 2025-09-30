from pydantic import BaseModel, EmailStr, Field, field_validator, UUID4
from typing import Literal
from datetime import datetime
import re
from typing import Optional, Dict, Any, Literal



class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: Literal["buyer", "supplier", "admin"] = "buyer"  # only allowed roles
    vat_number: str | None = None
    company_name: str
    name: str
    @field_validator("password")
    def validate_password_strength(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str                 # UUID as string
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

class VerificationToken(BaseModel):
    token: str
    user_id: str
    expires_at: datetime

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

LogLevel = Literal['DEBUG','INFO','WARNING','ERROR','CRITICAL','AUDIT']

class LogCreate(BaseModel):
    user_id: Optional[UUID4] = None
    level: LogLevel = 'INFO'
    action: str
    path: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class LogOut(BaseModel):
    id: UUID4
    user_id: Optional[UUID4]
    level: LogLevel
    action: str
    path: Optional[str]
    ip: Optional[str]
    user_agent: Optional[str]
    meta: Dict[str, Any]
    created_at: datetime

class LogListOut(BaseModel):
    items: list[LogOut]
    page: int
    page_size: int
    total: int
    pages: int