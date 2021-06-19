#!/usr/bin/env python3
from enum import Enum
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

class ServerExit(Enum):
    SUCCESS = 0
    FAIL = 1

class RebuildServer:
    def __init__(self):
        self.clients = {}
        self.games = {}
        self.exit = ServerExit.SUCCESS

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
                    # print('Connect: ', side, command, addr)
                elif command == 'login':
                    extra = extra.split(":", maxsplit=extra_len['login'])
                    addr, name, status = extra
                    status = status.rstrip("\n")
                    self.clients[addr] = name
                    # print('Login: ', side, command, addr, name, status)
                elif command == 'logout':
                    extra = extra.split(":", maxsplit=extra_len['logout'])
                    addr, name = extra
                    name = name.rstrip("\n")
                    self.clients[addr] = None
                    # print('Logout: ', side, command, addr, name)
                elif command == 'disconnect':
                    extra = extra.split(":", maxsplit=extra_len['disconnect'])
                    addr, status = extra
                    status = status.rstrip("\n")
                    del self.clients[addr]
                    # print('Disconnect: ', side, command, addr, status)
                elif command == 'begin':
                    extra = extra.split(":", maxsplit=extra_len['begin'])
                    addr1, name1, addr2, name2 = extra
                    name2 = name2.rstrip("\n")
                    self.games[name1+name2] = 0
                    # print('Begin: ', side, command, addr1, name1, addr2, name2)
                elif command == 'end':
                    extra = extra.split(":", maxsplit=extra_len['end'])
                    addr1, name1, addr2, name2, winner = extra
                    winner = winner.rstrip("\n")
                    del self.games[name1+name2]
                    # print('End: ', side, command, addr1, name1, addr2, name2, winner)
                elif command == 'close':
                    closeCounter += 1
        except IOError:
            pass
        if openCounter != closeCounter:
            self.exit = ServerExit.FAIL

    ''' Return a list with all connected clients '''
    def clients_connected(self):
        return self.clients.items()

    ''' Return a list with all games running '''
    def games_running(self):
        return self.games.keys()

    ''' Restablish connection with each client connected '''
    def restablish_connections(self, server):
        for address, username in self.clients_connected():
            print(f"Restablishing connection to {username} on {address}...")
            try:
                clientSocket, addr = server.servaddr.accept()
                if username == None: 
                    thread = threading.Thread(target = Connection, args = (clientSocket, addr, server))
                else:
                    user = server.users[username]
                    thread = threading.Thread(target = Connection, args = (clientSocket, addr, server, user))
                thread.daemon = True
                thread.start()
                server.log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")
            except socket.timeout:
                print(f"Client {address} cannot reconnect to the server due timeout (5s)!")
            except socket.error:
                print(f"Client {address} cannot reconnect to the server!")
