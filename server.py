#!/usr/bin/env python3
import socket
import threading
import datetime
from user import User

LISTENQ = 1
MAXLINE = 4096
BEATWAIT = 10
lock = threading.Lock()

def server(port):
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

    # Create a log file
    log = open("server.log", "w")
    log.write(f"[{datetime.datetime.now()}] Servidor iniciado na porta {port}!\n")

    users = []
    # Server waits for news connections
    while True:
        try:
            clientSocket, addr = servaddr.accept()
            thread = threading.Thread(target = handle_new_client, args = (clientSocket, addr, users, log))
            thread.daemon = True
            thread.start()
            log.write(f"[{datetime.datetime.now()}] Cliente {addr} conectado!\n")
        except KeyboardInterrupt:
            break

    # After all, we close the socket and the log
    print("Exiting the server")
    log.write(f"[{datetime.datetime.now()}] Servidor finalizado!\n")
    log.close()
    servaddr.close()


''' Server receives a heartbeat from clients every 10s '''
def handle_new_client(clientSocket, addr, users, log):
    # Timeout setted to detect an unexpected client disconnection
    clientSocket.settimeout(BEATWAIT)
    exit = False
    userLoggedIn = None
    while not exit:
        # Server communication with each client
        try:
            dataRecv = clientSocket.recv(MAXLINE).decode()
            if len(dataRecv) > 0:
                entries = dataRecv.split()
                command = entries[0]
                if command == "adduser":
                    if len(entries) == 3:
                        username = entries[1]
                        passwd = entries[2]
                        if findUser(username, users):
                            print("User already exists!")
                        else:
                            print("User created!")
                            userCreated = User(username, passwd)
                            lock.acquire()
                            users.append(userCreated)
                            lock.release()
                elif command == "passwd":
                    if len(entries) == 3:
                        if userLoggedIn:
                            print("New password setted!")
                            old_passwd = entries[1]
                            new_passwd = entries[2]
                            userLoggedIn.setPasswd(old_passwd, new_passwd)
                        else:
                            print("User not logged in!")
                elif command == "login":
                    if len(entries) == 3:
                        username = entries[1]
                        passwd = entries[2]
                        user = findUser(username, users)
                        if user:
                            if not user.logged_in:
                                if passwd == user.passwd:
                                    user.login(addr)
                                    userLoggedIn = user
                                else:
                                    print("Password incorrect")
                            else:
                                print("User logged in on other device")
                elif command == "leaders":
                    score_table = ''
                    for user in users:
                        score_table += user.username + "   " + str(user.score) + "\n"
                    if not score_table:
                        score_table = "There isn't any users registered"
                    clientSocket.send(score_table.encode())
                elif command == "list":
                    data = ''
                    for user in users:
                        if user.logged_in:
                            data += user.username + "\n"
                    if not data:
                        data = "There isn't any users online"
                    clientSocket.send(data.encode())
                elif command == "begin":
                    # TODO: Begin command
                    print("DEBUG: Begin")
                    if userLoggedIn:
                        if len(entries) == 2:
                            username = entries[1]
                            oponent = findUser(username, users)
                            if oponent:
                                if oponent.logged_in:
                                    print(oponent.addr, oponent.username) # DEBUG
                                    clientSocket.send(str(oponent.addr).encode())
                                else:
                                    clientSocket.send('User not logged in'.encode())
                            else:
                                clientSocket.send('User not found'.encode())
                        else:
                            clientSocket.send('The second argument must be an user'.encode())
                    else:
                        clientSocket.send('You need to log in first!'.encode())
                elif command == "send":
                    print("TODO: Send")
                elif command == "delay":
                    print("TODO: Delay")
                elif command ==  "end":
                    print("TODO: End")
                elif command == "logout":
                    if userLoggedIn:
                        userLoggedIn.logout()
                        userLoggedIn = None
                elif command == "exit":
                    if userLoggedIn:
                        userLoggedIn.logout()
                    exit = True
                elif command == "DISCONNECT":
                    if userLoggedIn:
                        userLoggedIn.logout()
                    exit = True
        except socket.timeout:
            # Heartbeat timeout (10s)
            log.write(f"[{datetime.datetime.now()}] Cliente {addr} desconectado inesperadamente!\n")
            exit = True
    log.write(f"[{datetime.datetime.now()}] Cliente {addr} desconectado!\n")
    clientSocket.close()


''' Find an user by username
    -> return: None or user '''
def findUser(username, users):
    for user in users:
        if user.username == username:
            return user
    return None
