#!/usr/bin/env python3
import socket
import threading
import datetime
from user import User

LISTENQ = 1
MAXLINE = 4096
BEATWAIT = 10

users = []
users_lock = threading.Lock()

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

    # Arquivo de log do servidor
    log = open("server.log", "w")
    log.write(f"[{datetime.datetime.now()}] server:open:{port}\n")

    # Loop do servidor para novas conexões
    while True:
        try:
            clientSocket, addr = servaddr.accept()
            thread = threading.Thread(target = handle_new_client, args = (clientSocket, addr, log))
            thread.daemon = True
            thread.start()
            log.write(f"[{datetime.datetime.now()}] client:connect:{addr}\n")
        except KeyboardInterrupt:
            break

    # Fecha o socket e adiciona no log
    print("Exiting the server")
    log.write(f"[{datetime.datetime.now()}] server:close\n")
    log.close()
    servaddr.close()


''' Server receives a heartbeat from clients every 10s '''
def handle_new_client(clientSocket, addr, log):
    # Timeout para desconexão inesperada (heartbeat)
    clientSocket.settimeout(BEATWAIT)

    stop = False
    loggedUser = None

    # Loop da conexão para receber comandos
    while not stop:
        try:
            dataRecv = clientSocket.recv(MAXLINE).decode()
            if len(dataRecv) > 0:
                entries = dataRecv.split()
                loggedUser, response, stop = processCommand(log, loggedUser, addr, entries[0], entries[1:])
                if response:
                    clientSocket.send(response.encode('ASCII'))

        except socket.timeout:
            # Timeout do heartbeat, desconecta cliente
            log.write(f"[{datetime.datetime.now()}] client:connlost:{addr}\n")
            stop = True

    log.write(f"[{datetime.datetime.now()}] client:disconnect:{addr}\n")
    clientSocket.close()


def processCommand(log, loggedUser, addr, command, args):
    response = None

    if command == "adduser":
        if len(args) == 2:
            username = args[0]
            passwd = args[1]
            if findUser(username):
                print(f"User {username} already exists!")
            else:
                print(f"User {username} created!")
                newUser = User(username, passwd)
                with users_lock:
                    users.append(newUser)
                log.write(f"[{datetime.datetime.now()}] user:create:{username},{passwd}\n")

    elif command == "passwd":
        if len(args) == 2:
            if loggedUser:
                old_passwd = args[0]
                new_passwd = args[1]
                if loggedUser.setPasswd(old_passwd, new_passwd):
                    print("New password set!")
                    log.write(f"[{datetime.datetime.now()}] user:passwd:{loggedUser.username},{new_passwd}\n")
                else:
                    print("Password doesn't match!")
            else:
                print("User not logged in!")

    elif command == "login":
        if len(args) == 2:
            username = args[0]
            passwd = args[1]
            user = findUser(username)
            if user:
                if not user.logged_in:
                    if passwd == user.passwd:
                        user.login(addr)
                        loggedUser = user
                        print(addr)
                        log.write(f"[{datetime.datetime.now()}] user:login:{username},{addr}\n")
                    else:
                        print("Password incorrect")
                else:
                    print("User logged in on other device")

    elif command == "leaders":
        score_table = ''
        with users_lock:
            for user in users:
                score_table += user.username + "   " + str(user.score) + "\n"
        if not score_table:
            score_table = "There isn't any users registered"
        response = score_table

    elif command == "list":
        data = ''
        with users_lock:
            for user in users:
                if user.logged_in:
                    data += user.username + "\n"
        if not data:
            data = "There isn't any users online"
        response = data

    elif command == "begin":
        if loggedUser:
            if len(args) == 1:
                username = args[0]
                oponent = findUser(username)
                if oponent:
                    if oponent.logged_in:
                        print(oponent.addr, oponent.username) # DEBUG
                        response = f"{oponent.addr}"
                    else:
                        response = "error:User not online"
                else:
                    response = 'error:User not found'

    elif command == "send":
        print("TODO: Send")

    elif command == "delay":
        print("TODO: Delay")

    elif command == "end":
        print("TODO: End")

    elif command == "logout":
        if loggedUser:
            loggedUser.logout()
            loggedUser = None

    elif command == "exit":
        if loggedUser:
            loggedUser.logout()
        return (None, None, True)

    elif command == "DISCONNECT":
        if loggedUser:
            loggedUser.logout()
        return (None, None, True)

    return (loggedUser, response, False)

''' Find an user by username
    -> return: None or user '''
def findUser(username):
    with users_lock:
        for user in users:
            if user.username == username:
                return user
    return None
