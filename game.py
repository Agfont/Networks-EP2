import numpy as np

MAXLINE = 4096

class Game:
    def __init__(self, sock, turn = False):
        self.board = np.zeros((3, 3), dtype='<U1')
        self.sock = sock
        self.turn = turn
        self.moves = 0

        if turn:
            self.char = 'X'
            self.opChar = 'O'
        else:
            self.char = 'O'
            self.opChar = 'X'

        self.end = False
        while not self.end:
            try:
                if turn:
                    entry = input("JogoDaVelha>")
                else:
                    entry = self.recv()
                if not entry:
                    continue
                entries = entry.split()
                self.processCommand(entry, entries[0], entries[1:])
            except KeyboardInterrupt:
                self.send('end')
                self.sock.close()
                self.end = True
        return

    def processCommand(self, raw_msg, cmd, args):
        if cmd == 'send':
            x = args[0] - 1
            y = args[1] - 1
            if self.turn:
                if self.isMoveValid(x, y):
                    self.send(raw_msg)
                    self.board[x, y] = self.char
                    self.moves += 1
                    self.turn = False
                else:
                    print(f"errrou")
            else:
                self.board[x, y] = self.opChar
                self.moves += 1
                self.turn = True
        elif cmd == 'delay':
            # TODO: checar tudo
            return
        elif cmd == 'end':
            return
        else:
            print('Comando inesperado')
            return

        # TODO: checar estado
        winner = self.checkWin()
        if winner:
            # TODO: endgame
            pass
        if self.checkDraw():
            # TODO: end game
            pass
        self.showBoard()

    def endGame(self):
        self.end = True

    def isMoveValid(self, x, y):
        return x in range(3) and y in range(3) and self.board[x, y] == ''

    def checkWin(self):
        for i in range(3):
            # Check line
            if self.board[i,0] == self.board[i,1] == self.board[i,2]:
                return self.board[i,0]
            # Check column
            if self.board[0,i] == self.board[1,i] == self.board[2,i]:
                return self.board[0,i]
        # Check diag 1
        if self.board[0,0] == self.board[1,1] == self.board[2,2]:
            return self.board[0,0]
        # Check diag 1
        if self.board[0,2] == self.board[1,1]  == self.board[2,0]:
            return self.board[0,2]
        return ''

    def checkDraw(self):
        return self.moves == 9

    def showBoard(self):
        # TODO: printar bonito
        print(self.board)

    def send(self, msg):
        self.sock.send(msg.encode('ASCII'))

    def recv(self):
        return self.sock.recv(MAXLINE).decode('ASCII')
