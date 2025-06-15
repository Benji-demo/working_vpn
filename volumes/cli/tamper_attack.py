#!/usr/bin/env python3
import socket
from scapy.all import *

SERVER_IP = "10.9.0.11"   # VPN server's IP in the Docker network
SERVER_PORT = 9090

# Craft a fake IP packet with spoofed content
ip = IP(src="192.168.60.5", dst="8.8.8.8")
udp = UDP(sport=12345, dport=53)
payload = b"THIS IS A TAMPERED PACKET"
pkt = ip / udp / Raw(load=payload)

# Send it directly to the VPN server's UDP port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(bytes(pkt), (SERVER_IP, SERVER_PORT))
print("🚨 Tampered packet sent to server!")
