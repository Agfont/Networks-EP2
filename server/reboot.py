#!/usr/bin/env python3
from server.connection import ClientServerConnection
import datetime
import socket
import threading

FIXED_HEADER = 3
extra_len = {
    'open' : 4 - FIXED_HEADER,
    'connect' : 3 - FIXED_HEADER,
    'login' : 5 - FIXED_HEADER,
    'logout' : 4 - FIXED_HEADER,
    'disconnect' : 4 - FIXED_HEADER,
    'begin' : 6 - FIXED_HEADER,
    'end' : 7 - FIXED_HEADER,
    'close' : 3 - FIXED_HEADER
}

class RebuildServer:
    def __init__(self):
        self.clients = {}
        self.serverCrashed = False
        self.exit = 'SUCCESS'

    def parseLog(self, log):
        openCounter = 0
        closeCounter = 0
        try:
            file = open(log)
            print("Processing log history...")
            for line in file:
                data = line.split(maxsplit=FIXED_HEADER-1)[2] # data = [<time> , <hour>, <side>:<command>:<addr\n> ]
                fields = data.split(":",maxsplit=FIXED_HEADER-1) # fields = [<side>, <command>, <addr\n>]
                side, command, extra = fields
                if command == 'open':
                    openCounter += 1
                elif command == 'connect':
                    addr = extra.rstrip("\n")
                    self.clients[addr] = None
                elif command == 'login':
                    extra = extra.split(":", maxsplit=extra_len['login'])
                    addr, name, status = extra
                    status = status.rstrip("\n")
                    self.clients[addr] = name
                elif command == 'logout':
                    extra = extra.split(":", maxsplit=extra_len['logout'])
                    addr, name = extra
                    name = name.rstrip("\n")
                    self.clients[addr] = None
                elif command == 'disconnect':
                    extra = extra.split(":", maxsplit=extra_len['disconnect'])
                    addr, status = extra
                    status = status.rstrip("\n")
                    del self.clients[addr]
                elif command == 'begin' or command == 'end':
                    pass
                elif command == 'close':
                    closeCounter += 1
        except IOError:
            pass
        if openCounter != closeCounter:
            self.serverCrashed = True
            self.exit = 'FAIL'

    ''' Return a list with all connected clients '''
    def clients_connected(self):
        return self.clients.items()

    ''' Restablish connection with each client connected '''
    def restablish_connections(self, server):
        for address, username in self.clients_connected():
            print(f"Restablishing connection to {username} on {address}...")
            try:
                clientSocket, addr = server.servaddr.accept()
                if username == None: 
                    thread = threading.Thread(target = ClientServerConnection, args = (clientSocket, addr, server))
                else:
                    user = server.users[username]
                    thread = threading.Thread(target = ClientServerConnection, args = (clientSocket, addr, server, user))
                thread.daemon = True
                thread.start()
                server.log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")
            except socket.timeout:
                print(f"Client {address} could not reconnect to the server due to timeout (5s)!")
            except socket.error:
                print(f"Client {address} could not reconnect to the server!")
        server.log.flush()
