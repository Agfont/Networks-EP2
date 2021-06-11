#!/usr/bin/env python3
import socket
import threading
import datetime
import os
import pandas as pd
from reboot import RebuildServer
from connection import Connection
from user import User

LISTENQ = 1
LOG = 'server.log'
DATABASE = 'data.csv'

class Server:
    def __init__(self, port):
        servaddr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servaddr.bind(('0.0.0.0', port))
        servaddr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servaddr.listen(LISTENQ)

        # Server information (IP)
        self.ip_addr = socket.gethostbyname(socket.gethostname())

        # 1) Parse Log
        rebuild = RebuildServer()
        rebuild.parseLog(LOG)

        # Arquivo de log do servidor
        self.log = open(LOG, "w")
        self.log.write(f"[{datetime.datetime.now()}] server:open:({self.ip_addr}, {port}):{rebuild.exit}\n")

        # 2) Restablish connections
        rebuild.restablish_connections(servaddr, self)

        # TODO: Recuperar users da DATABASE e atualizar variáveis
        self.users = {}
        self.users_lock = threading.Lock()

        if os.path.isfile(DATABASE):
            self.df = pd.read_csv(DATABASE)
            table = self.df[['User', 'Password', 'Score']].values
            for usr, pwd, score in table:
                user = User(usr, pwd)
                user.updateScore(score)
                self.users[usr] = user
        else:
            self.df = pd.DataFrame(columns = ['User', 'Password', 'Score'])

        # 3) Resume games and privileges

        # rebuild.resume_games()

        print(f"[Servidor no ar. Aguardando conexões na porta {port}]")
        print("[Para finalizar, pressione CTRL+c ou rode um kill ou killall]")
        # Loop that waits for new connections
        while True:
            try:
                clientSocket, addr = servaddr.accept()
                thread = threading.Thread(target = Connection, args = (clientSocket, addr, self))
                thread.daemon = True
                thread.start()
                self.log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")
            except KeyboardInterrupt:
                break

        # Close socket and log
        print("Exiting the server")
        self.log.write(f"[{datetime.datetime.now()}] server:close:({self.ip_addr}, {port})\n")
        self.log.close()
