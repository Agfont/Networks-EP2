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
                return
            username = args[0]
            passwd = args[1]
            with self.server.users_lock:
                if username in self.server.users[username]:
                    print(f"adduser: User {username} already exists!")
                else:
                    print(f"adduser: User {username} created!")
                    self.server.users[username] = User(username, passwd)
                    self.server.log.write(f"[{datetime.datetime.now()}] user:create:{username},{passwd}\n")

        elif command == "passwd":
            if len(args) != 2:
                print("passwd: Invalid message format")
                return
            if self.user:
                old_passwd = args[0]
                new_passwd = args[1]
                if self.user.setPasswd(old_passwd, new_passwd):
                    print("passwd: New password set!")
                    self.server.log.write(f"[{datetime.datetime.now()}] user:passwd:{self.user.username},{new_passwd}\n")
                else:
                    print("passwd: Password doesn't match!")
            else:
                print("passwd: User not logged in!")

        elif command == "login":
            if len(args) != 2:
                print("login: Invalid message format")
                return
            username = args[0]
            passwd = args[1]
            if username in self.server.users:
                user = self.server.users[username]
                if not user.logged_in:
                    if passwd == user.passwd:
                        user.login(self.addr)
                        self.user = user
                        print(self.addr)
                        print(f"login: User {username} logged in")
                        self.server.log.write(f"[{datetime.datetime.now()}] user:login:{username},{self.addr}\n")
                    else:
                        print("login: Password incorrect")
                else:
                    print("login: User logged in on another device")
            else:
                print("login: User doesn't exist")

        elif command == "leaders":
            score_table = ''
            with self.server.users_lock:
                for _, user in self.server.users:
                    score_table += user.username + "   " + str(user.score) + "\n"
            if not score_table:
                score_table = "There isn't any users registered"
            return score_table

        elif command == "list":
            data = ''
            with self.server.users_lock:
                for _, user in self.server.users:
                    if user.logged_in:
                        data += user.username + "\n"
            if not data:
                data = "There isn't any users online"
            self.send(data)

        elif command == "begin":
            if self.user:
                if len(args) == 1:
                    username = args[0]
                    oponent = self.server.users[username]
                    if oponent:
                        if oponent.logged_in:
                            print(oponent.addr, oponent.username) # DEBUG
                            self.send(f"{oponent.addr}")
                        else:
                            self.send("error:User not online")
                    else:
                        self.send('error:User not found')

        elif command == "send":
            print("TODO: Send")

        elif command == "delay":
            print("TODO: Delay")

        elif command == "end":
            print("TODO: End")

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
