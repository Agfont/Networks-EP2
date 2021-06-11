#!/usr/bin/env python3
import threading
import datetime
from connection import Connection
from enum import Enum

FIXED_HEADER = 3
extra_len = {
    'open' : 4 - FIXED_HEADER,
    'connect' : 3 - FIXED_HEADER,
    'login' : 5 - FIXED_HEADER,
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
        return self.clients.keys()

    ''' Return a list with users online (all logged in clients) '''
    def users_connected(self):
        return [v for v in self.clients.values() if (v != 0)]

    ''' Return a list with all games running '''
    def games_running(self):
        return self.games.keys()

    ''' Restablish connection with each client connected '''
    def restablish_connections(self, servaddr, server):
        for dict in self.clients_connected():
            clientSocket, addr = servaddr.accept()
            thread = threading.Thread(target = Connection, args = (clientSocket, addr, server))
            thread.daemon = True
            thread.start()
            server.log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")

    ''' Resume all games running, sending heartbeats to players '''
    def resume_games(self):
        list_games = self.games_running()
        # check if has any games running
        if len(list_games) > 0:
            # TODO: send heartbeats to players
            pass