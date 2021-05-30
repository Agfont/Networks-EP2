#!/usr/bin/env python3
import client
import server
import sys

def main(): 
    # python3 main.py <PORT>
    if(len(sys.argv) == 2):
        if (sys.argv[1].isdigit()): 
            server.server(int(sys.argv[1]))
        else:
            print('The second argument must be the port number')

    # python3 main.py <IP Adress> <PORT>
    # python3 main.py 192.168.15.25 8000
    elif(len(sys.argv) == 3):
        if (sys.argv[2].isdigit()): 
            client.client(sys.argv[1], int(sys.argv[2]))
        else:
            print('The third argument must be the port number')
        
    else:
        print('Invalid number of arguments')

if __name__ == "__main__":
    main()