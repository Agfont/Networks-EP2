#!/usr/bin/env python3
import socket
import time
import threading
from enum import Enum
import errno

LISTENQ = 1
MAXLINE = 4096
BEATWAIT = 5

class ClientState(Enum):
    EXIT   = 0
    PROMPT = 1
    INGAME = 2

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
        hb_thread = threading.Thread(target = self.heartbeat, args=(addr, port))
        hb_thread.daemon = True
        hb_thread.start()

        # Inicia socket de conexões P2P
        addr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr.bind(('', 0)) # Usa qualquer porta disponível
        addr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        addr.listen(LISTENQ)

        self.listenPort = addr.getsockname()[1]

        # Loop para novas conexões
        recvInvites_thread = threading.Thread(target = self.inviteLoop, args = (addr,))
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
                send(self.serverSocket, 'DISCONNECT')
                self.serverSocket.close()
                self.state = ClientState.EXIT

        self.serverSocket.close()
        return


    def processCommand(self, raw_msg, command, args):
        if command == "adduser":
            if len(args) != 2:
                print("Invalid message, expected: adduser <user> <passwd>")
                return
            send(self.serverSocket, raw_msg)
            checkAck(self.serverSocket)

        elif command == "passwd":
            if len(args) != 2:
                print("Invalid message, expected: passwd <old passwd> <new passwd>")
                return
            send(self.serverSocket, raw_msg)
            checkAck(self.serverSocket)

        elif command == "login":
            if len(args) != 2:
                print("Invalid message, expected: login <user> <passwd>")
                return
            send(self.serverSocket, raw_msg + f" {self.listenPort}")
            if (checkAck(self.serverSocket)):
                self.username = args[0]

        elif command == "leaders":
            send(self.serverSocket, raw_msg)
            data = receive(self.serverSocket)
            if len(data) > 0:
                print("|---------- Score Table ----------|")
                print("| User                | Score     |")
                print("|---------------------------------|")
                print(data)
                print("|---------------------------------|")

        elif command == "list":
            send(self.serverSocket, raw_msg)
            data = receive(self.serverSocket)
            if len(data) > 0:
                print("|------------ Players ------------|")
                print(data)
                print("|---------------------------------|")

        elif command == "begin":
            if len(args) != 1:
                print("Invalid message, expected: begin <oponente>")
                return
            send(self.serverSocket, raw_msg)

            data = receive(self.serverSocket)
            if data[0:3] != 'ack':
                print(data)
                return
            entries = entries[1].split()
            if len(entries) != 3:
                print("Unexpected server response format")
                return

            username = args[0]
            addr = entries[0]
            port = entries[1]

            self.oponentSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.oponentSocket.settimeout(10)
            try:
                self.serverSocket.connect((addr, port))
            except socket.timeout:
                print("Couldn't connect to oponent: connection timeout")
                return
            except socket.error:
                print("Couldn't connect to oponent")
                return

            send(self.oponentSocket, f"invite {self.username}")
            # TODO: Send invite
            return

        elif command == "send":
            print("No game to play")

        elif command == "delay":
            print("No oponent to measure delay")

        elif command ==  "end":
            print("No game to end")

        elif command == "logout":
            send(self.serverSocket, raw_msg)
            if (checkAck(self.serverSocket)):
                self.username = ""

        elif command == "exit":
            self.serverSocket.send('DISCONNECT'.encode())
            if (self.state == ClientState.INGAME):
                # TODO: end game
                pass
            self.state = ClientState.EXIT

    ''' Client sends a heartbeat to the sever every 5s '''
    def heartbeat(self, addr, port):
        while True:
            try:
                send(self.serverSocket, "Thump!")
                time.sleep(BEATWAIT)
            except IOError as e:
                # Handle Broken pipe
                if e.errno == errno.EPIPE:
                    print("\nServer disconnected")
                    self.serverSocket.close()
                    # TODO: Reestablish connection with server
                    '''reSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    reSocket.settimeout(180) # 3 min
                    try:
                        reSocket.connect((addr, port))
                        hb_thread = threading.Thread(target = heartbeat,args = (reSocket,))
                        hb_thread.daemon = True
                        hb_thread.start()
                    except socket.timeout:
                        print("Client cannot reconnect to the server due timeout (3 min)!")
                    except socket.error:
                        print("Client cannot reconnect to the server!")'''
                    break


    def inviteLoop(self, addr):
        while True:
            socket = addr.accept()

            if self.state != ClientState.PROMPT:
                print("opa kk")

            # TODO: Handle receive invite
            self.oponentSocket = socket
            print('invite received')
            send(socket, "end")



def checkAck(socket):
    data = receive(socket)
    if (data == 'ack'):
        return True
    print(f"Server error: {data}")
    return False


def send(socket, msg):
    socket.send(msg.encode('ASCII'))


def receive(socket):
    return socket.recv(MAXLINE).decode('ASCII')
