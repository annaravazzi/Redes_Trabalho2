import socket
import threading

class Server:
    def __init__(self, IP, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((IP, port))
        self.server_socket.listen()
        print(f"Server listening on {IP}:{port}")
    
    def accept_connections(self):
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection established with {client_address}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()
    
    def handle_client(self, client_socket):  
        is_connected = True
        while is_connected:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message == "EXIT":
                    print("Client requested to disconnect.")
                    client_socket.send("ACK: DISCONNECT".encode('utf-8'))
                    is_connected = False
                else:
                    print(f"Received message: {message}")
            except Exception as e:
                print(f"An error occurred: {e}")
                is_connected = False

        client_socket.close()

if __name__ == "__main__":
    server = Server("localhost", 12345)
    server.accept_connections()