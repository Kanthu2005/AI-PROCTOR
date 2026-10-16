from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    domain: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
