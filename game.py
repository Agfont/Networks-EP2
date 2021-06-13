import numpy as np
from enum import Enum

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

        if turn:
            self.char = 'X'
            self.opChar = 'O'
        else:
            self.char = 'O'
            self.opChar = 'X'

    def run(self):
        self.showBoard()
        self.state = MatchState.INGAME
        while self.state == MatchState.INGAME:
            try:
                if self.turn:
                    entry = input("JogoDaVelha>")
                    if not entry:
                        continue
                    entries = entry.split()
                    self.processCommand(entry, entries[0], entries[1:])
                else:
                    print("Waiting for opponent...")
                    entry = self.recv()
                    if not entry:
                        continue
                    entries = entry.split()
                    self.processMessage(entries[0], entries[1:])
            except KeyboardInterrupt:
                self.send('end')
                self.sock.close()
                self.state = MatchState.LOST
        return self.state.value

    def processCommand(self, raw_msg, cmd, args):
        if cmd == 'send':
            x = int(args[0]) - 1
            y = int(args[1]) - 1
            if self.isMoveValid(x, y):
                self.send(raw_msg)
                self.board[x, y] = self.char
                self.moves += 1
                self.turn = False
                self.showBoard()
                self.checkState()
            else:
                print("Invalid movement")
        elif cmd == 'delay':
            # TODO: checar tudo
            pass
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
            self.turn = True
            print(f"Opponent placed on {args[0]} {args[1]}")
            self.showBoard()
            self.checkState()
        elif cmd == 'end':
            print("Opponent quit the match!")
            self.state = MatchState.WON
            return
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

    def send(self, msg):
        self.sock.send(msg.encode('ASCII'))

    def recv(self):
        return self.sock.recv(MAXLINE).decode('ASCII')
