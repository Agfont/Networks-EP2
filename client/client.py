#!/usr/bin/env python3
from client.game import Game
from enum import Enum
import errno
import os
import socket
import threading
import time

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
        try:
            self.serverSocket.connect((addr, port))
        except socket.error:
            print("Client cannot connect to the server!")
            exit(1)

        self.up_event = threading.Event()
        self.up_event.set()

        # Thread to send heartbeats to the server
        hb_thread = threading.Thread(target = self.heartbeat, args=(addr, port))
        hb_thread.daemon = True
        hb_thread.start()

        # Start socket for P2P connection
        addr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr.bind(('', 0)) # Usa qualquer porta disponível
        addr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        addr.listen(LISTENQ)
        self.listenPort = addr.getsockname()[1]

        # Thread to receive invitations from other players
        recvInvites_thread = threading.Thread(target = self.inviteLoop, args = (addr,))
        recvInvites_thread.daemon = True
        recvInvites_thread.start()

        # Prompt for user interaction
        self.state = ClientState(ClientState.PROMPT)
        while self.state != ClientState.EXIT:
            try:
                entry = input("JogoDaVelha>")
                if (self.state == ClientState.INGAME):
                    self.processInvite(entry)
                    continue
                if not entry:
                    continue
                entries = entry.split()
                self.processCommand(entry, entries[0], entries[1:])
            except KeyboardInterrupt:
                try:
                    self.send(self.serverSocket, 'DISCONNECT')
                except IOError:
                    pass
                self.serverSocket.close()
                self.state = ClientState.EXIT

        self.serverSocket.close()
        return

    ''' Parse and handle commands typed by users on prompt '''
    def processCommand(self, raw_msg, command, args):
        if command == "adduser":
            if len(args) != 2:
                print("Invalid message, expected: adduser <user> <passwd>")
                return
            self.send(self.serverSocket, raw_msg)
            checkAck(self.serverSocket)

        elif command == "passwd":
            if len(args) != 2:
                print("Invalid message, expected: passwd <old passwd> <new passwd>")
                return
            self.send(self.serverSocket, raw_msg)
            checkAck(self.serverSocket)

        elif command == "login":
            if len(args) != 2:
                print("Invalid message, expected: login <user> <passwd>")
                return
            self.send(self.serverSocket, raw_msg + f" {self.listenPort}")
            if (checkAck(self.serverSocket)):
                self.username = args[0]

        elif command == "leaders":
            self.send(self.serverSocket, raw_msg)
            data = receive(self.serverSocket)
            if len(data) > 0:
                print("--- Score Board ---")
                print(data)

        elif command == "list":
            self.send(self.serverSocket, raw_msg)
            data = receive(self.serverSocket)
            if len(data) > 0:
                print("--- Online Players ---")
                print(data)

        elif command == "begin":
            if len(args) != 1:
                print("Invalid message, expected: begin <opponent>")
                return
            if args[0] == self.username:
                print("You can't send an invite to yourself")
                return
            self.send(self.serverSocket, raw_msg)
            data = receive(self.serverSocket)
            if data[0:3] != 'ack':
                print(data)
                return
            entries = data.split()
            if len(entries) != 3:
                print("Unexpected server response format")
                return
            username = args[0]
            addr = entries[1]
            port = int(entries[2])

            self.opponentSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.opponentSocket.settimeout(180) # 3 minutes to connect to opponent
            try:
                self.opponentSocket.connect((addr, port))
            except socket.timeout:
                print("Couldn't connect to opponent: connection timeout (3 min)")
                return
            except socket.error:
                print("Couldn't connect to opponent")
                return

            # Connection established with opponent
            self.send(self.opponentSocket, f"invite {self.username}")
            msg = receive(self.opponentSocket)
            if (msg != 'acc'):
                print('Opponent refused!')
                self.opponentSocket.close()
                self.opponentSocket = None
                return
            self.send(self.serverSocket, f"matchinit {self.username} ({addr},{port}) {username}")
            self.state = ClientState.INGAME
            state = self.beginGame(True)
            self.send(self.serverSocket, f"matchfin {state} {self.username} ({addr},{port}) {username}")

        elif command == "send":
            print("Not in match")

        elif command == "delay":
            print("No opponent to measure delay")

        elif command ==  "end":
            print("No game to end")

        elif command == "logout":
            self.send(self.serverSocket, raw_msg)
            if (checkAck(self.serverSocket)):
                self.username = ""

        elif command == "exit":
            self.serverSocket.send('DISCONNECT'.encode())
            self.state = ClientState.EXIT

    ''' Process invite answered by opponent '''
    def processInvite(self, entry):
        if (entry != 'y'):
            self.send(self.opponentSocket, 'nacc')
            self.state = ClientState.PROMPT
            self.opponentSocket.close()
            self.opponentSocket = None
            return
        self.send(self.opponentSocket, 'acc')
        self.beginGame()

    ''' Start a match, willBegin parameter controls which player will start '''
    def beginGame(self, willBegin = False):
        game = Game(self.opponentSocket, willBegin)
        state = game.run()
        self.opponentSocket.close()
        self.opponentSocket = None
        self.state = ClientState.PROMPT
        return state

    ''' Client sends a heartbeat to the sever every 5s '''
    def heartbeat(self, addr, port):
        reconnecting = False
        while not reconnecting:
            try:
                self.send(self.serverSocket, "Thump!", True)
                time.sleep(BEATWAIT)
            except IOError as e:
                # Server disconnected: Handle Broken pipe
                reconnecting = True
                self.up_event.clear()
                if e.errno == errno.EPIPE:
                    if self.state == ClientState.PROMPT:
                        print("\n-- Server disconnected")
                        print("JogoDaVelha>", end='', flush=True)
                    self.serverSocket.close()
                    self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    count = 0

                    # Reestablishing connection with server
                    while True:
                        try:
                            self.serverSocket.connect((addr, port))
                            if self.state == ClientState.PROMPT:
                                print("-- Connection reestablished with server!")
                                print("JogoDaVelha>", end='', flush=True)
                            reconnecting = False
                            self.up_event.set()
                            break
                        except socket.error:
                            pass
                            # print(f"-- Client trying to reconnect to the server: {count}s...")
                        time.sleep(1)
                        count += 1
                        if self.state == ClientState.INGAME:
                            count = 0
                        if count == 180:
                            print(f"-- Client cannot reconnect to the server due timeout ({count}s)!")
                            break
        print('Could not restablish connection, closing client...')
        os._exit(1)

    ''' Loop for receive invitations from other players. If user is in game, reject automatically. '''
    def inviteLoop(self, addr):
        while True:
            sock, _ = addr.accept()
            invite = receive(sock)

            if self.state != ClientState.PROMPT:
                self.send(sock, "nacc")
                sock.close()
                continue

            entries = invite.split()
            if (entries[0] != 'invite'):
                self.send(sock, "nacc")

            self.state = ClientState.INGAME
            self.opponentSocket = sock
            print()
            print(f"{entries[1]} is inviting you to a match, accept invite(y/N):", end=" ", flush=True)

    def send(self, sock, msg, force=False):
        if not force:
            try:
                self.up_event.wait()
                sock.send((msg + ';').encode('ASCII'))
            except IOError:
                return
        else:
            sock.send((msg + ';').encode('ASCII'))


def checkAck(sock):
    data = receive(sock)
    if (data == 'ack'):
        return True
    elif data == '': data = "Broken Pipe"
    print(f"Server error: {data}")
    return False

def receive(sock):
    # Clients shouldn't receive multiple messages before responding, so we can ignore the
    # possibility of receiving more than one command here
    return sock.recv(MAXLINE).decode('ASCII')[0:-1]
