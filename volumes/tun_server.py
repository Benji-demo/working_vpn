#!/usr/bin/env python3
from scapy.all import *
import socket

IP_A = "0.0.0.0"
PORT = 9090
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((IP_A, PORT))

while True:
    data, (ip, port) = sock.recvfrom(2048)
    pkt = IP(data)
    print("From {}:{} --> {}:{}".format(ip, port, IP_A, PORT))
    print("  Inside: {} --> {}".format(pkt.src, pkt.dst))

