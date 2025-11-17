import socket
import threading
from macros import BUFF_SIZE, DIR_SERVER, Commands, Status
from hash import calc_hash

class Server:
    def __init__(self, IP, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Cria socket do servidor
        self.server_socket.bind((IP, port)) 
        self.server_socket.listen()
        print(f"Server listening on {IP}:{port}")
        self.execute()
    
    def execute(self):
        """
        Loop principal do servidor para aceitar conexões de clientes.
        """
        while True:
            print("Waiting for client requests...")
            client_socket, client_address = self.server_socket.accept()     # Cria socket para o cliente
            print(f"Connection established with {client_address}")
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))  # Inicia thread para tratar o cliente
            client_thread.start()
    
    def handle_client(self, client_socket):  
        """
        Trata a comunicação com o cliente.
        """
        while True:
            try:
                msg = client_socket.recv(BUFF_SIZE)    # Recebe dados do cliente
            except ConnectionResetError:
                print("Client disconnected abruptly.")
                break
            try:
                command = msg.decode('utf-8').split()[0]  # Extrai comando da mensagem
            except UnicodeDecodeError or IndexError:
                self.send(client_socket, Status.BAD_REQUEST)
                print("ERROR: Unable to decode client message.")
                continue

            if command == Commands.EXIT:    # Cliente deseja desconectar
                print("Client requested to disconnect.")
                break   # Sai do loop e fecha a conexão

            elif command == Commands.GET_FILE:
                try:
                    filename = msg.decode('utf-8').split(' ')[1]
                    print(f"Client requested file: {filename}")
                    self.send_file(client_socket, filename)
                except UnicodeDecodeError or IndexError:
                    self.send(client_socket, Status.BAD_REQUEST)
                    print("ERROR: Unable to parse filename from client request.")
                    continue

        self.close(client_socket)
        return

    def load_file(self, filename):
        """
        Carrega o arquivo solicitado do sistema de arquivos.
        Retorna os dados do arquivo em bytes e seu tamanho.
        """
        try:
            with open(DIR_SERVER + filename, 'rb') as file:
                f = file.read()
                return f, len(f), calc_hash(f)
        except FileNotFoundError:
            return None, 0
    
    def send_file(self, client_socket, filename):
        """
        Envia o arquivo solicitado ao cliente em segmentos.
        """
        file_data, file_size, hash_value = self.load_file(filename)
        print(hash_value)

        if file_data is None:
            self.send(client_socket, Status.NOT_FOUND)
            print(f"ERROR: File {filename} not found.")
            return
        
        # Header
        try:
            status = Status.OK.to_bytes(1)
            filename_bytes = filename.encode('utf-8')
            filename_len = len(filename_bytes).to_bytes(2)
            file_size_bytes = file_size.to_bytes(8)
        except OverflowError:
            print(f"ERROR: Header too large to send.")
            self.send(client_socket, Status.HEADER_TOO_LARGE)
            return

        header = status + filename_len + filename_bytes + file_size_bytes + hash_value
        if len(header) > BUFF_SIZE:
            self.send(client_socket, Status.HEADER_TOO_LARGE)
            print("ERROR: Header too large to send.")
            return

        # Envia o header primeiro
        self.send(client_socket, header)

        # Envia os pacotes do arquivo
        for i in range(0, len(file_data), BUFF_SIZE):
            self.send(client_socket, file_data[i:i + BUFF_SIZE])
        
    def send(self, client_socket, message):
        """
        Envia uma mensagem ao cliente.
        """
        if isinstance(message, int):    # Código de status
            message = message.to_bytes(1)
        elif isinstance(message, str):  # Mensagem de texto
            message = message.encode('utf-8')

        client_socket.sendall(message)

    def close(self, client_socket):
        """
        Fecha o socket do cliente.
        """
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            client_socket.close()

if __name__ == "__main__":
    server = Server("localhost", 12345)