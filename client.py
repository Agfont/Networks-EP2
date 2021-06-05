#!/usr/bin/env python3
import socket
import time
import threading
from enum import Enum

MAXLINE = 4096
BEATWAIT = 5

class ClientState(Enum):
    EXIT     = 0
    PROMPT   = 1
    PREGAME  = 2
    INGAME   = 3
    POSTGAME = 4

class Client:
    def __init__(self, addr, port):
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.settimeout(10)

        try:
            self.serverSocket.connect((addr, port))
        except socket.timeout:
            print("Client cannot connect to the server due timeout (10s)!")
            exit(1)
        except socket.error:
            print("Client cannot connect to the server!")
            exit(2)

        # Inicia heartbeat
        hb_thread = threading.Thread(target = self.heartbeat)
        hb_thread.daemon = True
        hb_thread.start()

        # Inicia espera por convites
        recvInvites_thread = threading.Thread(target = self.p2p)
        recvInvites_thread.daemon = True
        recvInvites_thread.start()

        self.state = ClientState(ClientState.PROMPT)
        while self.state != ClientState.EXIT:
            try:
                entry = input("JogoDaVelha>")
                entries = entry.split()
                if entries == []:
                    continue
                self.processCommand(entry, entries[0], entries[1:])
            except KeyboardInterrupt:
                self.serverSocket.send('DISCONNECT'.encode())
                self.serverSocket.close()
                self.state = ClientState.EXIT


    def processCommand(self, raw_msg, command, args):
        if command == "adduser":
            if len(args) != 2:
                print("Invalid message, expected: adduser <usuario> <senha>")
                return
            self.send(raw_msg)

        elif command == "passwd":
            if len(args) != 2:
                print("Invalid message, expected: passwd <senha antiga> <senha nova>")
                return
            self.send(raw_msg)

        elif command == "login":
            if len(args) != 2:
                print("Invalid message, expected: login <usuario> <senha>")
                return
            self.send(raw_msg)

        elif command == "leaders":
            self.send(raw_msg)
            data = self.receive()
            if len(data) > 0:
                print("|----- Score Table -----|")
                print("| User      | Score     |")
                print("|-----------------------|")
                print(data)
                print("|-----------------------|")

        elif command == "list":
            self.send(raw_msg)
            data = self.receive()
            if len(data) > 0:
                print("|------- Players -------|")
                print(data)
                print("|-----------------------|")

        elif command == "begin":
            if len(args) != 1:
                print("Invalid message, expected: begin <oponente>")
                return
            self.send(raw_msg)
            entries = self.receive().split()
            if len(entries) != 2:
                print("Unexpected server response")
                return
            self.start_match(entries[0], entries[1])

        elif command == "send":
            print("TODO: Send")

        elif command == "delay":
            print("TODO: Delay")

        elif command ==  "end":
            self.send(raw_msg)

        elif command == "logout":
            self.send(raw_msg)

        elif command == "exit":
            self.serverSocket.send('DISCONNECT'.encode())
            self.serverSocket.close()
            self.state = "exit"


    def send(self, msg):
        self.serverSocket.send(msg.encode('ASCII'))


    def receive(self):
        return self.serverSocket.recv(MAXLINE).decode()


    def heartbeat(self):
        while True:
            msg = 'Thump!'.encode('ASCII')
            self.serverSocket.send(msg)
            time.sleep(BEATWAIT)


    def start_match(self, username, addr):
        print("DEBUG:")
        print(username)
        print(addr)
        return


    def p2p(self):
        # while True:
        #     msg, addr = socket.recvfrom(MAXLINE)
        #     msg = msg.decode()
        #     print(msg)
        #     if len(msg) > 0:
        #         entries = msg.split()
        #         if entries == []:
        #             continue
        #         command = entries[0]
        #         # TODO: Invites
        #         if command == "INVITE":
        #             print("DATA RECEIVED: ", msg)
        #             msg = input("Do you want to play? (y/n)")
        #             if msg == "y":
        #                 socket.sendto("ACCEPTED".encode(), addr)
        #             else:
        #                 socket.sendto("DENIED".encode(), addr)
