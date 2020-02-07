from typing import List

from pydantic import BaseModel, EmailStr, ValidationError, validator, Field
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, password):
        if len(password) < 7:
            raise ValueError(f'password a least 7 characters long')
        return password


class VirtualMachineBase(BaseModel):
    image: str


class VirtualMachineCreate(VirtualMachineBase):
    pass


class VirtualMachine(VirtualMachineBase):
    id: int
    vm_id: int
    user_id: int
    creation_date: datetime
    data: dict = Field(None)

    class Config:
        orm_mode = True


class User(UserBase):
    id: int
    is_active: bool
    virtual_machines: List[VirtualMachine] = []

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str = None
