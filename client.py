#!/usr/bin/env python3
import socket
import threading
import errno
import time
from enum import Enum
from game import Game, MatchState

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
        print(f"port: {addr.getsockname()[1]}")

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
                send(self.serverSocket, 'DISCONNECT')
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
                print("Invalid message, expected: begin <opponente>")
                return
            if args[0] == self.username:
                print("You can't send an invite to yourself")
                return
            send(self.serverSocket, raw_msg)
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
            self.opponentSocket.settimeout(180)

            try:
                self.opponentSocket.connect((addr, port))
            except socket.timeout:
                print("Couldn't connect to opponent: connection timeout")
                return
            except socket.error:
                print("Couldn't connect to opponent")
                return

            send(self.opponentSocket, f"invite {self.username}")
            msg = receive(self.opponentSocket)
            if (msg != 'acc'):
                print('Opponent refused!')
                self.opponentSocket.close()
                self.opponentSocket = None
                return
            self.state = ClientState.INGAME
            state = self.beginGame(True);
            send(self.serverSocket, f"matchfin {state} {self.username} {username}")

        elif command == "send":
            print("Not in match")

        elif command == "delay":
            print("No opponent to measure delay")

        elif command ==  "end":
            print("No game to end")

        elif command == "logout":
            send(self.serverSocket, raw_msg)
            if (checkAck(self.serverSocket)):
                self.username = ""

        elif command == "exit":
            self.serverSocket.send('DISCONNECT'.encode())
            self.state = ClientState.EXIT

    def processInvite(self, entry):
        if (entry != 'y'):
            send(self.opponentSocket, 'nacc')
            self.state = ClientState.PROMPT
            self.opponentSocket.close()
            self.opponentSocket = None
            return
        send(self.opponentSocket, 'acc')
        self.beginGame()

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
                send(self.serverSocket, "Thump!")
                time.sleep(BEATWAIT)
            except IOError as e:
                reconnecting = True
                # Server disconnected: Handle Broken pipe
                if e.errno == errno.EPIPE:
                    print("\n-- Server disconnected")
                    self.serverSocket.close()
                    self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    count = 0

                    # Reestablishing connection with server
                    while True:
                        time.sleep(1)
                        count += 1
                        try:
                            self.serverSocket.connect((addr, port))
                            # TODO: Receive heartbeat and talk with server about games runing
                            print("-- Connection reestablished")
                            reconnecting = False
                            break
                        except socket.error:
                            print(f"-- Client trying to reconnect to the server: {count}s...")
                        if count == 5:
                            print(f"-- Client cannot reconnect to the server due timeout ({count}s)!")
                            break

    def inviteLoop(self, addr):
        while True:
            sock, _ = addr.accept()
            invite = receive(sock)

            if self.state != ClientState.PROMPT:
                send(sock, "nacc")
                sock.close()
                continue

            entries = invite.split()
            if (entries[0] != 'invite'):
                send(sock, "nacc")

            self.state = ClientState.INGAME
            self.opponentSocket = sock
            print()
            print(f"{entries[1]} is inviting you to a match, accept invite(y/N):", end=" ", flush=True)


def checkAck(sock):
    data = receive(sock)
    if (data == 'ack'):
        return True
    print(f"Server error: {data}")
    return False

def send(sock, msg):
    sock.send(msg.encode('ASCII'))

def receive(sock):
    return sock.recv(MAXLINE).decode('ASCII')
