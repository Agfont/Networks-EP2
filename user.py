#!/usr/bin/env python3
''' Class to store user information'''
class User:
    def __init__(self, username):
        self.username = username
        self.logged_in = False
        self.addr = None

    def __str__(self):
        return self.username

    def login(self, addr, port):
        self.logged_in = True
        self.addr = addr
        self.port = port

    def logout(self):
        self.logged_in = False