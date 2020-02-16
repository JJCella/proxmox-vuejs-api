from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime

from .database import Base


class VirtualMachine(Base):
    __tablename__ = "vms"

    id = Column(Integer, primary_key=True, index=True)
    vmid = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'))
    #image = Column(String)
    creation_date = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    virtual_machines = relationship("VirtualMachine")