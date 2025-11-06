import socket

class Client:
    def __init__(self, IP, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((IP, port))
        print(f"Connected to server at {IP}:{port}")
    
    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"An error occurred: {e}")
    
    def close_connection(self):
        while True:
            response = self.client_socket.recv(1024)  # Wait for ACK from server
            if response.decode('utf-8') == "ACK: DISCONNECT":
                print("Server acknowledged disconnection.")
                self.client_socket.close()
                print("Connection closed.")
                return
    
if __name__ == "__main__":
    client = Client("localhost", 12345)
    client.send_message("Hello, Server!")
    input("Press Enter to send EXIT command...")
    client.send_message("EXIT")
    client.close_connection()