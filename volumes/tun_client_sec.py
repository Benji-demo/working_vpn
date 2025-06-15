#!/usr/bin/env python3

import os, fcntl, struct, socket, select, hashlib, sys, atexit
from scapy.all import *

SECRET = sys.stdin.readline().strip().encode()

def add_hash(packet):
    h = hashlib.sha256(SECRET + packet).digest()
    return packet + h

def verify_hash(data):
    if len(data) < 32:
        return False, b''
    packet, recv_hash = data[:-32], data[-32:]
    calc_hash = hashlib.sha256(SECRET + packet).digest()
    return (recv_hash == calc_hash), packet

def cleanup(ifname):
    os.system(f"ip link del {ifname} 2>/dev/null")

# === TUN Setup ===
TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000

tun = os.open("/dev/net/tun", os.O_RDWR)
ifr = struct.pack('16sH', b'bini%d', IFF_TUN | IFF_NO_PI)
ifname = fcntl.ioctl(tun, TUNSETIFF, ifr).decode('UTF-8')[:16].strip('\x00')
print("TUN interface:", ifname)

os.system(f"ip link set dev {ifname} up")
os.system(f"ip route add 192.168.53.0/24 dev {ifname}")

# === UDP Setup ===
SERVER_IP = "10.9.0.11"
SERVER_PORT = 9090
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# === Step 1: Authenticate
auth_msg = b'AUTH:' + SECRET
sock.sendto(add_hash(auth_msg), (SERVER_IP, SERVER_PORT))
print("🔐 Sent authentication packet")

# === Step 2: Wait for ASSIGN_IP or NO_IP ===
while True:
    data, _ = sock.recvfrom(2048)
    ok, packet = verify_hash(data)
    if ok and packet.startswith(b"ASSIGN_IP:"):
        client_ip = packet.decode().split(":")[1]
        print(f"✅ Assigned IP from server: {client_ip}")
        print("AUTH_RESULT:True", flush=True)
        print(f"ASSIGN_IP:{client_ip}", flush=True)
        break
    elif ok and packet.startswith(b"NO_IPS_AVAILABLE"):
        print("❌ Server has no IPs left to assign.")
        print("AUTH_RESULT:False", flush=True)
        sys.exit(1)
    else:
        print("⏳ Waiting for valid IP assignment...")

# === Step 3: Configure the TUN interface
os.system(f"ip addr add {client_ip}/24 dev {ifname}")

atexit.register(cleanup, ifname)

# === Step 4: Main loop ===
while True:
    ready, _, _ = select.select([tun, sock], [], [])
    for fd in ready:
        if fd == tun:
            packet = os.read(tun, 2048)
            ip = IP(packet)
            print("From TUN ==>", ip.summary())
            sock.sendto(add_hash(packet), (SERVER_IP, SERVER_PORT))

        elif fd == sock:
            data, _ = sock.recvfrom(2048)
            ok, packet = verify_hash(data)
            if ok:
                ip = IP(packet)
                print("From socket <==", ip.summary())
                os.write(tun, packet)
            else:
                print("Packet failed integrity check. Dropped.")