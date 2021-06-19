#!/usr/bin/env python3
import socket
import threading
import datetime
import os
import pandas as pd
from reboot import RebuildServer
from connection import ClientServerConnection
from user import User

LISTENQ = 1
LOG = 'server.log'
DATABASE = 'data.csv'

class Server:
    def __init__(self, port):
        # Socket server inicialization
        self.servaddr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servaddr.bind(('0.0.0.0', port))
        self.servaddr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servaddr.listen(LISTENQ)
        self.ip_addr = socket.gethostbyname(socket.gethostname())

        # Rebuild server state after crash (if needed) 
        rebuild = RebuildServer()
        rebuild.parseLog(LOG)

        self.log = open(LOG, "w")
        self.log.write(f"[{datetime.datetime.now()}] server:open:({self.ip_addr}, {port}):{rebuild.exit}\n")

        # Charge users on memory with a dictionary
        self.users = {}
        self.users_lock = threading.Lock()
        if os.path.isfile(DATABASE):
            self.df = pd.read_csv(DATABASE)
            table = self.df['User']
            for usr in table:
                user = User(usr)
                self.users[usr] = user
        else:
            self.df = pd.DataFrame(columns = ['User', 'Password', 'Score'])
        self.df_lock = threading.Lock()

        # Restablish connections and privileges
        self.servaddr.settimeout(5) # Limit to 5 seconds for reconnect to each client
        rebuild.restablish_connections(self)
        self.servaddr.settimeout(None) # Clear timeout

        print(f"[Servidor no ar. Aguardando conexões na porta {port}]")
        print("[Para finalizar, pressione CTRL+c ou rode um kill ou killall]")
        # Loop that waits for new connections
        while True:
            try:
                clientSocket, addr = self.servaddr.accept()
                thread = threading.Thread(target = ClientServerConnection, args = (clientSocket, addr, self))
                thread.daemon = True
                thread.start()
                self.log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")
            except KeyboardInterrupt:
                break

        # Close socket and log
        print("Exiting the server")
        self.log.write(f"[{datetime.datetime.now()}] server:close:({self.ip_addr}, {port})\n")
        self.log.close()
