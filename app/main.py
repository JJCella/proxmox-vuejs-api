from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

from datetime import datetime, timedelta

from passlib.hash import bcrypt

import random

from enum import Enum

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND

from starlette.middleware.cors import CORSMiddleware

from proxmoxer import ProxmoxAPI

from concurrent.futures import ThreadPoolExecutor

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

models.Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

node = 'atlas'

pool = ThreadPoolExecutor()

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8081",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

new_vm = {
    "vmid": "144",
    "name": "aa",
    # "ide2":"local:iso/debian-10.1.0-amd64-netinst.iso,media=cdrom",
    "ostype": "l26",
    # "scsihw":"virtio-scsi-pci",
    # "scsi0": "local-lvm:1",
    "sockets": "1",
    "cores": "1",
    # "numa":"0",
    "memory": "512",
    # "net0":"virtio,bridge=vmbr0,firewall=1"
}


# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_proxmox():
    try:
        proxmox = ProxmoxAPI('192.168.1.2', user='fastapi@pam',
                             password='fastapi', verify_ssl=False).nodes(node)
        yield proxmox
    finally:
        pass


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = crud.get_user_by_email(db, email=email)
    if not user:
        return False
    if not bcrypt.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(*, data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except PyJWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user


@app.get("/users/me/vms", response_model=List[schemas.VirtualMachineInfos])
async def read_own_vms(current_user: schemas.User = Depends(get_current_user), proxmox=Depends(get_proxmox)):
    vms = []
    for vm in current_user.virtual_machines:
        vm.__dict__.update(proxmox.qemu(str(vm.vmid)).status.current.get())
        vms.append(vm.__dict__)
    return vms


@app.get("/users/me/vms/{vm_id}", response_model=schemas.VirtualMachineInfos)
async def read_own_vm(vm_id, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db),
                      proxmox=Depends(get_proxmox)):
    vm = crud.get_user_vm(db, current_user.id, vm_id)
    if vm:
        vm.__dict__.update(proxmox.qemu(str(vm.vmid)).status.current.get())
        print(vm.__dict__)
        return vm.__dict__
    raise HTTPException(status_code=HTTP_404_NOT_FOUND)


class Status(str, Enum):
    stop = 'stop'
    start = 'start'


@app.get("/users/me/stats", response_model=schemas.Stats)
async def get_own_stats(current_user: schemas.User = Depends(get_current_user),
                       db: Session = Depends(get_db), proxmox=Depends(get_proxmox)):
    instances = 0
    down_instances = 0
    up_instances = 0

    for vm in current_user.virtual_machines:
        status = proxmox.qemu(str(vm.vmid)).status.current.get()['status']
        instances += 1
        if status == 'stopped':
            down_instances +=1
        if status == 'running':
            up_instances +=1
    return {'instances' : instances, 'monthly_costs' : instances*5, 'down_instances': down_instances, 'up_instances': up_instances}


    nb_instances: int
    up_instances: int
    down_instances: int
    monthly_costs: int

@app.post("/users/me/vms/{vm_id}/{status}", response_model=schemas.VirtualMachineInfos)
async def start_own_vm(vm_id, status: Status, current_user: schemas.User = Depends(get_current_user),
                       db: Session = Depends(get_db), proxmox=Depends(get_proxmox)):
    vm = crud.get_user_vm(db, current_user.id, vm_id)
    if vm:
        if status == Status.start:
            proxmox.qemu(str(vm.vmid)).status.start.post()
        if status == Status.stop:
            proxmox.qemu(str(vm.vmid)).status.stop.post()

        vm.__dict__.update(proxmox.qemu(str(vm.vmid)).status.current.get())
        return vm.__dict__
    raise HTTPException(status_code=HTTP_404_NOT_FOUND)


@app.post("/users/me/vms", response_model=schemas.VirtualMachine)
async def create_vm(vm: schemas.VirtualMachineCreate, current_user: schemas.User = Depends(get_current_user),
                    db: Session = Depends(get_db), proxmox: ProxmoxAPI = Depends(get_proxmox)):
    new_vm['vmid'] = str(random.randint(1000, 9999999))
    new_vm['name'] = vm.name

    vm = schemas.VirtualMachineBaseCreation(**new_vm)

    db_vm = crud.create_user_vm(db, vm, current_user.id)
    if db_vm:
        pool.submit(proxmox.qemu.post(**new_vm))
        return db_vm
    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)


@app.put("/users/me/vms/{vm_id}", response_model=schemas.VirtualMachineInfos)
async def update_vm(vm_id, vm: schemas.VirtualMachineCreate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db),  proxmox: ProxmoxAPI = Depends(get_proxmox)):
    db_vm = crud.get_user_vm(db, current_user.id, vm_id)
    if db_vm:
        proxmox.qemu(str(db_vm.vmid)).config.put(**vm.dict())
        db_vm.__dict__.update(proxmox.qemu(str(db_vm.vmid)).status.current.get())
        return db_vm.__dict__
    raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/users/me/vms/{vm_id}")
async def destroy_vm(vm_id, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db),  proxmox: ProxmoxAPI = Depends(get_proxmox)):
    db_vm = crud.get_user_vm(db, current_user.id, vm_id)
    if db_vm:
        db.delete(db_vm)
        db.commit()
        proxmox.qemu(str(db_vm.vmid)).delete()
    raise HTTPException(status_code=HTTP_404_NOT_FOUND)
