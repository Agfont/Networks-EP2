#!/usr/bin/env python3
from client.game import MatchState
from server.user import User
import datetime
import socket

MAXLINE = 4096
BEATWAIT = 10
DATABASE = 'server/data/data.csv'

''' Class to handle each user connected with the server'''
class ClientServerConnection:
    def __init__(self, clientSocket, addr, server, user = None):
        self.socket = clientSocket
        self.addr = addr
        self.server = server
        self.user = user
        self.stop = False
        self.exit = 'purposeful'

        # Timeout to detect unexpected disconnection (Heartbeat)
        self.socket.settimeout(BEATWAIT)

        # Loop for client communication
        while not self.stop:
            try:
                msgs = receive(self.socket).split(';')
                for msg in msgs:
                    if not msg: continue
                    entries = msg.split()
                    self.processCommand(entries[0], entries[1:])
            except socket.timeout:
                self.stop = True
                self.exit = 'unexpected'

        self.server.log.write(f"[{datetime.datetime.now()}] client:disconnect:{self.addr}:{self.exit}\n")
        self.server.log.flush()
        self.socket.close()

    def processCommand(self, command, args):
        if command == "adduser":
            if len(args) != 2:
                send(self.socket, "Invalid message format")
                return
            username = args[0]
            passwd = args[1]
            with self.server.users_lock:
                if username in self.server.users:
                    send(self.socket, f"User {username} already exists")
                    return
                self.server.users[username] = User(username)
                send(self.socket, "ack")

                # Update database
                entry = {'User' : username,
                         'Password' : passwd,
                         'Score':   0}
                with self.server.df_lock:
                    self.server.df = self.server.df.append(entry, ignore_index=True)
                    self.server.df.to_csv(DATABASE, index = False)

        elif command == "passwd":
            if len(args) != 2:
                send(self.socket, "Invalid message format")
                return
            if not self.user:
                send(self.socket, "You must log in first")
                return
            old_passwd = args[0]
            new_passwd = args[1]
            if str(self.server.df.loc[self.server.df['User'] == self.user.username, 'Password'].item()) != old_passwd:
                send(self.socket, "Password doesn't match")
                return
            send(self.socket, "ack")

            # Update database
            with self.server.df_lock:
                self.server.df.loc[self.server.df['User'] == self.user.username, 'Password'] = new_passwd
                self.server.df.to_csv(DATABASE, index=False)

        elif command == "login":
            if len(args) != 3:
                send(self.socket, "Invalid message format")
                return
            username = args[0]
            passwd = args[1]
            port = args[2]
            if self.user:
                send(self.socket, "You must log out first")
                self.logLogin(username, "failed")
                return
            if username not in self.server.users:
                send(self.socket, "User doesn't exist")
                self.logLogin(username, "failed")
                return
            user = self.server.users[username]
            if user.logged_in:
                send(self.socket, "User logged in on your or other device")
                self.logLogin(username, "failed")
                return
            with self.server.df_lock:
                if str(self.server.df.loc[self.server.df['User'] == user.username, 'Password'].item()) != passwd:
                    send(self.socket, "Password incorrect")
                    self.logLogin(username, "failed")
                    return
            user.login(self.addr, port)
            self.user = user
            self.logLogin(username, "success")
            send(self.socket, "ack")

        elif command == "leaders":
            send(self.socket, self.server.df.loc[:, ['User', 'Score']].to_string(index=False))

        elif command == "list":
            userList = ''
            with self.server.users_lock:
                for username, user in self.server.users.items():
                    if user.logged_in:
                        userList += f"{user.username}\n"
            if not userList:
                userList = "No user online\n"
            send(self.socket, userList[:-1])

        elif command == "begin":
            if len(args) != 1:
                send(self.socket, "Invalid message")
                return
            if not self.user:
                send(self.socket, "You must be log in first")
                return
            username = args[0]
            if self.user.username == username:
                send(self.socket, "You can't invite yourself")
                return
            if username not in self.server.users:
                send(self.socket, "Opponent doesn't exist")
                return
            opponent = self.server.users[username]
            if not opponent or not opponent.logged_in:
                send(self.socket, "Opponent not available")
                return
            send(self.socket, f"ack {self.user.username} {opponent.addr[0]} {opponent.port}")

        elif command == "matchinit":
            if len(args) != 3:
                return
            host = args[0]
            guest_addr = args[1]
            guest = args[2]

            # First is 'X' (who sent the invite), second is 'O' (who received the invite)
            self.server.log.write(f"[{datetime.datetime.now()}] client:begin:{self.addr}:{host}:{guest_addr}:{guest}\n")
            self.server.log.flush()

        elif command == "matchfin":
            if len(args) != 4:
                return
            matchState = MatchState(int(args[0]))
            host = args[1]
            guest_addr = args[2]
            guest = args[3]
            winner = 'DRAW'

            with self.server.df_lock:
                if matchState == MatchState.DRAW:
                    self.server.df.loc[self.server.df['User'] == host, 'Score'] += 1
                    self.server.df.loc[self.server.df['User'] == guest, 'Score'] += 1
                elif matchState == MatchState.WON:
                    self.server.df.loc[self.server.df['User'] == host, 'Score'] += 2
                    winner = host
                elif matchState == MatchState.LOST:
                    self.server.df.loc[self.server.df['User'] == guest, 'Score'] += 2
                    winner = guest

                self.server.df.to_csv(DATABASE, index=False)
                self.server.log.write(f"[{datetime.datetime.now()}] client:end:{self.addr}:{host}:{guest_addr}:{guest}:{winner}\n")
                self.server.log.flush()

        elif command == "logout":
            if self.user:
                self.user.logout()
                self.server.log.write(f"[{datetime.datetime.now()}] client:logout:{self.addr}:{self.user.username}\n")
                self.server.log.flush()
                self.user = None
                send(self.socket, "ack")
                return
            send(self.socket, "User not logged in")

        elif command == "exit":
            if self.user:
                self.user.logout()
                self.server.log.write(f"[{datetime.datetime.now()}] client:logout:{self.addr}:{self.user.username}\n")
                self.server.log.flush()
            self.stop = True

    def logLogin(self, username, status):
        self.server.log.write(f"[{datetime.datetime.now()}] client:login:{self.addr}:{username}:{status}\n")
        self.server.log.flush()

def send(socket, msg):
    socket.send((msg + ';').encode('ASCII'))

def receive(socket):
    return socket.recv(MAXLINE).decode('ASCII')
