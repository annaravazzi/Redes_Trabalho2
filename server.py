import socket
import threading
from macros import BUFF_SIZE, Commands, Status
import hash

class Server:
    def __init__(self, IP, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((IP, port))
        self.server_socket.listen()
        print(f"Server listening on {IP}:{port}")
        self.accept_connections()
    
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
                data = client_socket.recv(BUFF_SIZE)
                h, msg = hash.get_hash_msg(data)
                if not hash.verify_hash(msg, h):
                    self.send(client_socket, Status.BAD_REQUEST)
                if msg.decode('utf-8') == Commands.EXIT:
                    print("Client requested to disconnect.")
                    is_connected = False
                elif(msg.split()[0] == Commands.GET_FILE):
                    filename = msg.split()[1]
                    file_data, file_size = self.load_file(filename)

            except Exception as e:
                print(f"An error occurred: {e}")
                is_connected = False

        client_socket.close()

    def load_file(self, filename):
        try:
            with open(filename, 'rb') as file:
                f = file.read()
                return f, len(f)
        except FileNotFoundError:
            print(f"File {filename} not found.")
            return None, 0
        
    def send(self, client_socket, message):
        encapsulated_msg = hash.encapsulate(message)
        client_socket.send(encapsulated_msg)

if __name__ == "__main__":
    server = Server("localhost", 12345)