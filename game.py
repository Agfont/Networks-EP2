from datetime import datetime
from enum import Enum
import numpy as np
import threading
import time

MAXLINE = 4096

class MatchState(Enum):
    INGAME = 0
    DRAW   = 1
    WON    = 2
    LOST   = 3

class Game:
    def __init__(self, sock, turn = False):
        self.board = np.zeros((3, 3), dtype='<U1')
        self.board.fill(' ')
        self.sock = sock
        self.turn = turn
        self.moves = 0
        self.delays = []
        self.delays_lock = threading.Lock()
        self.pong_event = threading.Event()

        if turn:
            self.char = 'X'
            self.opChar = 'O'
        else:
            self.char = 'O'
            self.opChar = 'X'

    def run(self):
        self.showBoard()
        self.state = MatchState.INGAME

        # Start the receive thread
        recv_thread = threading.Thread(target = self.recvLoop)
        recv_thread.daemon = True
        recv_thread.start()

        # Start the ping thread
        recv_thread = threading.Thread(target = self.pingLoop)
        recv_thread.daemon = True
        recv_thread.start()

        while self.state == MatchState.INGAME:
            try:
                if not self.turn: continue
                entry = input("JogoDaVelha>")
                if not entry: continue
                entries = entry.split()
                self.processCommand(entry, entries[0], entries[1:])
            except KeyboardInterrupt:
                self.state = MatchState.LOST
                self.send('end')
                self.sock.close()
        return self.state.value

    def recvLoop(self):
        while self.state == MatchState.INGAME:
            try:
                msgs = self.receive().split(';')
                for entry in msgs:
                    if not entry: continue
                    entries = entry.split()
                    self.processMessage(entries[0], entries[1:])
            except:
                return

    def pingLoop(self):
        while self.state == MatchState.INGAME:
            try:
                self.sendPing()
                self.pong_event.wait()
                self.pong_event.clear()
                time.sleep(5)
            except:
                return

    def processCommand(self, raw_msg, cmd, args):
        if cmd == 'send':
            x = int(args[0]) - 1
            y = int(args[1]) - 1
            if self.isMoveValid(x, y):
                self.send(raw_msg)
                self.board[x, y] = self.char
                self.moves += 1
                self.showBoard()
                self.checkState()
                self.turn = False
            else:
                print("Invalid movement")
        elif cmd == 'delay':
            print("Last three delays:")
            for delay in self.delays:
                print(f"{int(delay * 100)}ms")
        elif cmd == 'end':
            self.send('end')
            self.state = MatchState.LOST
        else:
            print("Unexpected command")

    def processMessage(self, cmd, args):
        if cmd == 'send':
            x = int(args[0]) - 1
            y = int(args[1]) - 1
            self.board[x, y] = self.opChar
            self.moves += 1
            print(f"Opponent placed on {args[0]} {args[1]}")
            self.showBoard()
            self.checkState()
            self.turn = True
        elif cmd == 'end':
            print("Opponent quit the match!")
            self.state = MatchState.WON
        elif cmd == 'ping':
            self.send('pong')
        elif cmd == 'pong':
            now = datetime.now()
            with self.delays_lock:
                self.delays.append((now - self.pingSentTime).total_seconds() / 2) # delay should be rtt / 2
                if len(self.delays) > 3:
                    self.delays.pop(0)
            self.pingSentTime = None
            self.lastPing = now
            self.pong_event.set()
        else:
            self.send("?")

    def checkState(self):
        winner = self.checkWin()
        if winner:
            print(f"{winner} won the match!")
            if self.char == winner:
                self.state = MatchState.WON
            else:
                self.state = MatchState.LOST
        if self.checkDraw():
            print("The match drawed!")
            self.state = MatchState.DRAW

    def isMoveValid(self, x, y):
        return x in range(3) and y in range(3) and self.board[x, y] == ' '

    def checkWin(self):
        for i in range(3):
            # Check line
            if self.board[i,0] != ' ' and self.board[i,0] == self.board[i,1] == self.board[i,2]:
                return self.board[i,0]
            # Check column
            if self.board[0,i] != ' ' and self.board[0,i] == self.board[1,i] == self.board[2,i]:
                return self.board[0,i]
        # Check diag 1
        if self.board[0,0] != ' ' and self.board[0,0] == self.board[1,1] == self.board[2,2]:
            return self.board[0,0]
        # Check diag 1
        if self.board[0,2] != ' ' and self.board[0,2] == self.board[1,1]  == self.board[2,0]:
            return self.board[0,2]
        return ''

    def checkDraw(self):
        return self.moves == 9

    def showBoard(self):
        print(f"{self.board[0, 0]} │ {self.board[0, 1]} │ {self.board[0, 2]}")
        print("──┼───┼──")
        print(f"{self.board[1, 0]} │ {self.board[1, 1]} │ {self.board[1, 2]}")
        print("──┼───┼──")
        print(f"{self.board[2, 0]} │ {self.board[2, 1]} │ {self.board[2, 2]}")

    def sendPing(self):
        self.pingSentTime = datetime.now()
        self.send('ping')

    def send(self, msg):
        self.sock.send((msg + ';').encode('ASCII'))

    def receive(self):
        return self.sock.recv(MAXLINE).decode('ASCII')
