#!/usr/bin/env python3
from server import Server
from client import Client
import sys

def main(): 
    # python3 main.py <PORT>
    if(len(sys.argv) == 2):
        if (sys.argv[1].isdigit()): 
            Server(int(sys.argv[1]))
        else:
            print('The second argument must be a port number')

    # python3 main.py <IP Adress> <PORT>
    elif(len(sys.argv) == 3):
        if (sys.argv[2].isdigit()):
            Client(sys.argv[1], int(sys.argv[2]))
        else:
            print('The third argument must be a port number')
        
    else:
        print('Invalid number of arguments')

if __name__ == "__main__":
    main()