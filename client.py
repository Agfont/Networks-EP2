#!/usr/bin/env python3
from ast import parse
import socket
import time
import threading

MAXLINE = 4096
BEATWAIT = 5

def client(addr, port):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.settimeout(10)

    # p2pSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        clientSocket.connect((addr, port))
        hb_thread = threading.Thread(target=heartbeat,args=(clientSocket,))
        hb_thread.daemon = True
        hb_thread.start()
        
        '''p2p_thread = threading.Thread(target=p2p,args=(p2pSocket,))
        p2p_thread.daemon = True
        p2p_thread.start()'''

    except socket.timeout:
        print("Client cannot connect to the server due timeout (10s)!")
        exit()
    except socket.error:
        print("Client cannot connect to the server!")
        exit()
    
    state = None
    while state != "exit":
        ''' Client communication with server '''
        try:
            entry = input("JogoDaVelha>")
            entries = entry.split()
            if entries == []:
                continue
            command = entries[0]
            if command == "adduser":
                if len(entries) == 3:
                    clientSocket.send(entry.encode())
            elif command == "passwd":
                if len(entries) == 3:
                    clientSocket.send(entry.encode())
            elif command == "login":
                if len(entries) == 3:
                    clientSocket.send(entry.encode())
            elif command == "leaders":
                clientSocket.send(entry.encode())
                data = clientSocket.recv(MAXLINE).decode()
                if len(data) > 0:
                    print("----- Score Table -----")
                    print("  User  |  Score")
                    print(data)
                    print("-----------------------")
            elif command == "list":
                clientSocket.send(entry.encode())
                data = clientSocket.recv(MAXLINE).decode()
                if len(data) > 0:
                    print("----- Players -----")
                    print(data)
                    print("-------------------")      
            elif command == "begin":
                clientSocket.send(entry.encode())
                data = clientSocket.recv(MAXLINE).decode()
                if len(data) > 0:
                    print("----- IP Opponent -----")
                    print(data)
                    print("-------------------")   
            # P2P Communication  
            elif command == "send":
                print("TODO: Send")
            elif command == "delay":
                print("TODO: Delay")
            elif command ==  "end":
                clientSocket.send(entry.encode())
            elif command == "logout":
                clientSocket.send(entry.encode())
            elif command == "exit":
                clientSocket.send('DISCONNECT'.encode())
                clientSocket.close()
                state = "exit"
        except KeyboardInterrupt:
            clientSocket.send('DISCONNECT'.encode())
            clientSocket.close()
            state = "exit"

''' Client sends a heartbeat to the sever every 5s '''
def heartbeat(socket):
    while True:
        socket.send('Thump!'.encode())
        #print("Heartbet sent (By client)!") 
        time.sleep(BEATWAIT)

''' P2P for communication between clients '''
def p2p(socket, addr):
    while True:
        data = socket.recvfrom((MAXLINE).decode(), addr)
'''
def inviteToPlay(socket, addr):
    socket.settimeout(None)
    while True:
        data = socket.recvfrom((MAXLINE).decode(), addr)
        entries = data.split()
        if entries == []:
            continue
        command = entries[0]
        if command == "INVITE":
            print(data)
            msg = input("Do you want to play? (y/n)")
            if msg == "y":
                socket.sendto("ACCEPTED".encode(), addr)
            else:
                socket.sendto("DENIED".encode(), addr)'''