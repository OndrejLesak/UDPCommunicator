import socket


connection_socket = None


def initConnection():
    global connection_socket

    connection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(dest_ip, dest_port, message):
    connection_socket.sendto(message, (dest_ip, dest_port))
    data, addr = connection_socket.recvfrom(1024)
    print(f"Server message: {data.decode()}")


def main():
    initConnection()
    send('127.0.0.1', 5005, b"It works!")


if __name__ == "__main__":
    main()