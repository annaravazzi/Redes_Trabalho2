import socket
from macros import BUFF_SIZE, DIR_CLIENT, Commands, Status
from hash import verify_hash

class Client():
    def __init__(self, IP, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Cria socket do cliente
        self.client_socket.connect((IP, port))      # Conecta ao servidor dado
        print(f"Connected to server at {IP}:{port}")    
        self.execute()
    
    def execute(self):
        """
        Loop principal do cliente para comunicação com o servidor.
        """
        while True:
            req = input("Enter command (GET_FILE <filename> or EXIT): ")

            self.send_message(req)  # Envia comando ao servidor

            if req == Commands.EXIT:    # Cliente deseja desconectar, sai do loop
                print("Disconnecting from server.")
                break

            try:
                response = self.client_socket.recv(BUFF_SIZE)   # Recebe resposta do servidor
            except ConnectionResetError:
                print("ERROR: Connection to server lost.")
                break

            status, data = self.parse_response(response)    # Parseia a resposta do servidor

            # Erro na resposta
            if status is None:
                print("ERROR: Invalid response from server. Try again")
                continue
            
            # Resposta OK do servidor
            if status == Status.OK:
                # Dados inválidos
                if data is None:
                    print("ERROR: No valid data received from server. Try again.")
                    continue

                filename, filesize, hash_value = data
                # Recebe o arquivo do servidor
                self.receive_file(filename, filesize, hash_value)

            else:   # Resposta de erro do servidor
                if status == Status.BAD_REQUEST:
                    print("ERROR: Bad request sent to server. Try again.")
                elif status == Status.NOT_FOUND:
                    print("ERROR: Requested file not found on server.")
                elif status == Status.HEADER_TOO_LARGE:
                    print("ERROR: Header too large. Reduce filename or file size.")
                else:
                    print("ERROR: Unknown response from server. Try again.")
        
                
        # Fecha o socket do cliente ao sair do loop
        self.close()

    def parse_response(self, data):
        """
        Parseia a resposta do servidor.
        Retorna o status e os outros dados recebidos.
        """
        try:
            status = int.from_bytes(data[:1])   # Extrai o status da resposta
        except IndexError or ValueError:
            return None, None
        
        if status != Status.OK:     # Se não for OK, não há mais dados
            return status, None
        
        try:
            # Separa os campos do cabeçalho e os dados do arquivo seguindo o protocolo
            filename_len = int.from_bytes(data[1:3])
            filename = data[3:3 + filename_len].decode('utf-8')
            filesize = int.from_bytes(data[3 + filename_len:11 + filename_len])
            hash_value = data[11 + filename_len:43 + filename_len]

            return status, (filename, filesize, hash_value)
        except IndexError or ValueError:
            return status, None
        
    def receive_file(self, filename, filesize, hash_value):
        """
        Recebe o arquivo do servidor em pacotes e verifica o hash.
        """
        received_data = b''

        # Continua recebendo dados até completar o tamanho do arquivo
        while len(received_data) < filesize:
            try:
                packet = self.client_socket.recv(BUFF_SIZE)     # Socket TCP -> pacotes em ordem e sem perdas
            except ConnectionResetError:
                print("ERROR: Connection to server lost during file transfer. Aborting.")
                return
           
            received_data += packet   # Adiciona os dados do arquivo recebido
        
        # Verifica o hash dos dados recebidos
        if verify_hash(received_data, hash_value):
            # Salva o arquivo recebido no diretório do cliente
            with open(DIR_CLIENT + filename, 'wb') as file:
                file.write(received_data)
            print(f"File '{filename}' received successfully and saved to '{DIR_CLIENT}'.")
        else:
            print(hash_value)
            print("ERROR: Hash verification failed. File may be corrupted.")

        
    def close(self):
        """
        Fecha o socket do cliente.
        """
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.client_socket.close()


    def send_message(self, message):
        self.client_socket.send(message.encode('utf-8'))
    
if __name__ == "__main__":
    client = Client("localhost", 12345)
