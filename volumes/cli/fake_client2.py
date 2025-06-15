#!/usr/bin/env python3
import socket
from scapy.all import *

SERVER_IP = "10.9.0.11"
SERVER_PORT = 9090

# Spoofed packet from a fake "VPN client"
ip = IP(src="192.168.53.250", dst="8.8.8.8")
icmp = ICMP()
pkt = ip / icmp / b"PING from rogue"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(bytes(pkt), (SERVER_IP, SERVER_PORT))
print("🚨 Unauthorized packet sent to server!")
