from sqlalchemy.orm import Session

from passlib.hash import bcrypt
from random import randint

from . import models, schemas


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(email=user.email, hashed_password=bcrypt.hash(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_vms(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.VirtualMachine).offset(skip).limit(limit).all()


def create_user_vm(db: Session, item: schemas.VirtualMachineCreate, user_id: int):
    db_vm = models.VirtualMachine(**item.dict(), user_id=user_id)
    db_vm.vm_id = randint(1, 9999)
    db.add(db_vm)
    db.commit()
    db.refresh(db_vm)
    return db_vm

def get_user_vm(db: Session, user_id: int):
    pass

