import socket


SERVER_IP = '127.0.0.1'
SERVER_PORT = 5005
DEFAULT_TIMEOUT = 10

server_socket = None


def initServer(): # method intializes server
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))


def main():
    initServer()

    if server_socket is not None:
        try:
            server_socket.settimeout(DEFAULT_TIMEOUT)

            # keep alive
            while True:
                data, addr = server_socket.recvfrom(1500)
                if int(data.decode()) == 2:
                    print('Keep alive received')
                    server_socket.sendto('2'.encode(), addr)
                    break
                break


            while True:
                data, addr = server_socket.recvfrom(1500)
                server_socket.sendto('Data received'.encode(), addr)

        except socket.timeout:
            print('Session expired due to inactivity.\nShutting down')
            server_socket.close()

    else:
        print('Connection unsuccessful, try restarting the server')


if __name__ == '__main__':
    main()