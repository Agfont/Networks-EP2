#!/usr/bin/env python3
import socket
import threading
import datetime
from user import User

LISTENQ = 1
MAXLINE = 4096
BEATWAIT = 10

class Server:
    def __init__(self, port):
        ''' Agora é necessário informar: endereço IP, interface e porta.
            O socket ficará esperando conexões nesta porta e neste(s) endereços. 
            - socket (IPv4, TCP)
            - bind(IP Adress, Port)
            - listen(Listen Queue)
        '''
        servaddr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servaddr.bind(('', port))
        servaddr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Important
        servaddr.listen(LISTENQ)

        print(f"[Servidor no ar. Aguardando conexões na porta {port}]")
        print("[Para finalizar, pressione CTRL+c ou rode um kill ou killall]")

        # Arquivo de log do servidor
        self.log = open("server.log", "w")
        self.log.write(f"[{datetime.datetime.now()}] server:open:{port}\n")

        # TODO: Guardar users em um arquivo
        self.users = {}
        self.users_lock = threading.Lock()

        # Loop do servidor para novas conexões
        while True:
            try:
                clientSocket, addr = servaddr.accept()
                thread = threading.Thread(target = Connection, args = (clientSocket, addr, self))
                thread.daemon = True
                thread.start()
                self.log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")
            except KeyboardInterrupt:
                break

        # Fecha o socket e adiciona no log
        print("Exiting the server")
        self.log.write(f"[{datetime.datetime.now()}] server:close\n")
        self.log.close()
        servaddr.close()


class Connection:
    def __init__(self, clientSocket, addr, server):
        self.socket = clientSocket
        self.addr = addr
        self.server = server
        self.user = None
        self.stop = False

        # Timeout para desconexão inesperada (heartbeat)
        self.socket.settimeout(BEATWAIT)

        # Loop da conexão para receber comandos
        while not self.stop:
            try:
                dataRecv = self.receive()
                if len(dataRecv) > 0:
                    entries = dataRecv.split()
                    self.processCommand(entries[0], entries[1:])
            except socket.timeout:
                # Timeout do heartbeat, desconecta cliente
                self.server.log.write(f"[{datetime.datetime.now()}] client:connlost:{addr}\n")
                self.stop = True

        self.server.log.write(f"[{datetime.datetime.now()}] client:disconnect:{addr}\n")
        self.socket.close()


    def processCommand(self, command, args):
        if command == "adduser":
            if len(args) != 2:
                print("adduser: Invalid message format")
                self.send("Invalid message format")
                return
            username = args[0]
            passwd = args[1]
            with self.server.users_lock:
                if username in self.server.users:
                    print(f"adduser: User {username} already exists!")
                    self.send(f"User {username} already exists!")
                    return
                print(f"adduser: User {username} created!")
                self.server.users[username] = User(username, passwd)
                self.server.log.write(f"[{datetime.datetime.now()}] user:create:{username},{passwd}\n")
                self.send("ack")

        elif command == "passwd":
            if len(args) != 2:
                print("passwd: Invalid message format")
                self.send("Invalid message format")
                return
            if not self.user:
                print("passwd: User not logged in!")
                self.send("User not logged in")
                return
            old_passwd = args[0]
            new_passwd = args[1]
            if not self.user.setPasswd(old_passwd, new_passwd):
                print("passwd: Password doesn't match!")
                self.send("Password doesn't match")
                return
            print("passwd: New password set!")
            self.server.log.write(f"[{datetime.datetime.now()}] user:passwd:{self.user.username},{new_passwd}\n")
            self.send("ack")

        elif command == "login":
            if len(args) != 3:
                print("login: Invalid message format")
                self.send("Invalid message format")
                return
            username = args[0]
            passwd = args[1]
            port = args[2]
            if username not in self.server.users:
                print("login: User doesn't exist")
                self.send("User doesn't exist")
                return
            user = self.server.users[username]
            if user.logged_in:
                print("login: User logged in on another device")
                self.send("User logged in on another device")
                return
            if passwd != user.passwd:
                print("login: Password incorrect")
                self.send("Password incorrect")
                return
            user.login(self.addr, port)
            self.user = user
            print(self.addr)
            print(f"login: User {username} logged in")
            self.server.log.write(f"[{datetime.datetime.now()}] user:login:{username},{self.addr}\n")
            self.send("ack")

        elif command == "leaders":
            score_table = ''
            with self.server.users_lock:
                for username, user in self.server.users.items():
                    score_table += f"| {username:<20}| {user.score:<10}|\n"
            if not score_table:
                score_table = "| No user registered              |\n"
            self.send(score_table[:-1])

        elif command == "list":
            userList = ''
            with self.server.users_lock:
                for username, user in self.server.users.items():
                    if user.logged_in:
                        userList += f"| {user.username:<32}|\n"
            if not userList:
                userList = "| No user online                  |\n"
            self.send(userList[:-1])

        elif command == "begin":
            if len(args) != 1:
                self.send("Invalid message")
                return
            if not self.user:
                self.send("User not logged in")
                return
            username = args[0]
            oponent = self.server.users[username]
            if not oponent or not oponent.logged_in:
                self.send("error:Invalid oponent")
            self.send(f"ack {oponent.addr[0]} {oponent.port}")

        elif command == "logout":
            if self.user:
                self.user.logout()
                self.user = None

        elif command == "exit":
            if self.user:
                self.user.logout()
            return

        elif command == "DISCONNECT":
            if self.user:
                self.user.logout()
            return


    def send(self, msg):
        self.socket.send(msg.encode('ASCII'))


    def receive(self):
        return self.socket.recv(MAXLINE).decode('ASCII')
