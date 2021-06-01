#!/usr/bin/env python3
''' User information'''
class User:
    def __init__(self, username, passwd):
        self.username = username
        self.passwd = passwd
        self.logged_in = False
        self.is_playing = False
        self.score = 0
        self.addr = None

    def __str__(self):
        return self.username

    def setPasswd(self, old_passwd, new_passwd):
        if old_passwd == self.passwd:
            self.passwd = new_passwd
        else:
            print("Old password incorrect!")

    def login(self, addr):
        self.logged_in = True
        self.addr = addr

    def logout(self):
        self.logged_in = False

    def updateScore(self, points):
        self.score += points
