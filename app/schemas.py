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


class VirtualMachineCreate(BaseModel):
    name: str

class VirtualMachineBaseCreation(BaseModel):
    vmid: int

class VirtualMachine(BaseModel):
    id: int
    vmid: int
    user_id: int
    creation_date: datetime

    class Config:
        orm_mode = True

class Stats(BaseModel):
    instances: int
    up_instances: int
    down_instances: int
    monthly_costs: int

class VirtualMachineInfos(BaseModel):
    id: int
    creation_date: datetime
    name: str
    status: str
    uptime: int
    netin: int
    netout: int
    maxmem: int
    maxdisk: int
    mem: int
    cpu: int

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
