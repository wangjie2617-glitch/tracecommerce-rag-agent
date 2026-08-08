"""Administrator-facing user management schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

UserRoleName = Literal["admin", "customer_service", "operator"]


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=120)
    role: UserRoleName


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role: UserRoleName | None = None
    is_active: bool | None = None
