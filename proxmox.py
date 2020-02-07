from pydantic import BaseModel, EmailStr, ValidationError, validator
from proxmoxer import ProxmoxAPI, ResourceException
import time
from random import randint

node = 'poggersnode1'

proxmox = ProxmoxAPI('192.168.1.100', user='root@pam',
                     password='EeZ{e0da', verify_ssl=False)

x = proxmox.nodes(node).qemu(101).status.current.get()


class VirtualMachine(BaseModel):
    name: str
    uptime: int
    status: str
    cpu: float

#print(x)

#print(VirtualMachine(**x))

x = proxmox.nodes('poggersnode1').qemu(101).rrddata.get(timeframe='hour', cf='AVERAGE')

#print(x)

new_vm = {
 "vmid": "100",
 "name":"aa",
 "ide2":"local:iso/debian-10.1.0-amd64-netinst.iso,media=cdrom",
 "ostype":"l26",
 "scsihw":"virtio-scsi-pci",
 "scsi0":"local-lvm:10",
 "sockets":"1",
 "cores":"1",
 "numa":"0",
 "memory":"512",
 "net0":"virtio,bridge=vmbr0,firewall=1"
          }

try:
    result = proxmox.nodes(node).qemu.post(**new_vm)
except ResourceException as e:
    print(e)
else:
    print(result)

vm_infos = proxmox.nodes(node).qemu(new_vm['vmid']).status.current.get()

while 'lock' in vm_infos:
    time.sleep(1)
    print(vm_infos['lock'])
    vm_infos = proxmox.nodes(node).qemu(new_vm['vmid']).status.current.get()

vm_infos = proxmox.nodes(node).qemu(new_vm['vmid']).status.start.post()

print(vm_infos)

vm_infos = proxmox.nodes(node).qemu(new_vm['vmid']).status.stop.post()

print(vm_infos)

#print(proxmox.nodes(node).qemu(new_vm['vmid']).delete())