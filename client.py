"""
Módulo cliente para comunicação com o servidor usando TCP.
Envia requests de arquivos e mensagens de chat ao servidor e processa as respostas recebidas.
"""

from host import Host
import threading
from macros import DIR_CLIENT, Commands, Status
from hash import verify_hash

class Client(Host):
    def __init__(self, IP, port):
        super().__init__()
        try:
            self.tcp_socket.connect((IP, port))      # Conecta ao servidor dado
        except Exception as e:
            print(f"Failed to connect to server at {IP}:{port}: {e}")
            return
        print(f"Connected to server at {IP}:{port}")

        self.shutdown_event = threading.Event()     # Evento para sinalizar encerramento

        # Inicia thread em segundo plano para receber as respostas do servidor
        self.recv_thread = threading.Thread(target=self.receiver_loop, daemon=False)
        self.recv_thread.start()

        self.execute()
    
    def execute(self):
        """
        Loop principal do cliente para comunicação com o servidor (requests).
        """
        try:
            while True:
                print("Select command:")
                print("1. GET_FILE <filename>")
                print("2. CHAT <message>")
                print("3. EXIT")
                sel = input()

                # Encerra loop se sinal de encerramento foi setado
                if self.shutdown_event.is_set():
                    break

                if sel == '1':
                    filename = input("Enter filename to get: ")
                    # req = f"{Commands.GET_FILE} {filename}"
                    req = f"{Commands.WRONG_COMMAND} {filename}"      # Para testar comando inválido
                    filename = ""
                elif sel == '2':
                    message = input("Enter chat message: ")
                    req = f"{Commands.CHAT} {str(len(message))} {message}"
                    message = ""
                elif sel == '3':
                    req = Commands.EXIT
                else:
                    print("Invalid command. Please try again.")
                    continue
                
                try:
                    self.send_message(self.tcp_socket, req)  # Envia request ao servidor
                except ConnectionError:
                    print("Connection to server lost.")
                    break

                if req.startswith(Commands.EXIT):    # Cliente deseja desconectar, sai do loop
                    print("Disconnecting from server.")
                    break

        except KeyboardInterrupt:
            print("Disconnecting from server.")     # Encerramento via Ctrl+C
        finally:
            # Seta o sinal de encerramento
            self.shutdown_event.set()
            try:
                # Fecha socket e aguarda thread de recepção terminar antes de dar join
                try:
                    addr = self.tcp_socket.getpeername()
                except Exception:
                    addr = None
                self.close_socket(self.tcp_socket, addr)
            except Exception:
                pass
            try:
                if self.recv_thread.is_alive():
                    self.recv_thread.join(timeout=2.0)
            except Exception:
                pass

    def receiver_loop(self):
        """
        Thread em segundo plano para receber mensagens do servidor.
        """
        while True:
            # Encerra loop se sinal de encerramento foi setado
            if self.shutdown_event.is_set():
                break

            data = self.receive_message(self.tcp_socket)    # Recebe dados do servidor
            if data is None:
                print("Connection to server lost.")
                break
            if data == "TIMEOUT":
                continue

            # Processa a mensagem recebida
            status, content = self.parse_response(data)

            # Mensagem de chat
            if status == Commands.CHAT:
                message_len, message = content
                try:
                    # Consome o restante da mensagem (se não veio completa)
                    while len(message) < message_len:
                        if self.shutdown_event.is_set():
                            raise Exception
                        remaining = self.receive_message(self.tcp_socket, message_len - len(message))
                        if remaining is None:
                            print("Connection to server lost.")
                            raise Exception
                        if remaining == "TIMEOUT":
                            continue
                        try:
                            message += remaining.decode('utf-8')    # Adiciona parte recebida

                        except UnicodeDecodeError:
                            pass
                except Exception:   # Exceção geral para sair do loop (conexão perdida ou encerramento)
                    break

                # Printa mensagem de chat recebida do server
                print(f"[SERVER] {message}")    

            # Resposta de arquivo
            elif status == Status.OK:
                filename, file_size, hash_value, file_data = content
                try:
                    # Consome o restante do arquivo (se não veio completo)
                    while file_size > len(file_data):
                        if self.shutdown_event.is_set():
                            raise Exception
                        remaining = self.receive_message(self.tcp_socket, file_size - len(file_data))
                        if remaining is None:
                            print("Connection to server lost.")
                            raise Exception
                        if remaining == "TIMEOUT":
                            continue
                       
                        file_data += remaining  # Adiciona parte recebida

                except Exception:   # Exceção geral para sair do loop (conexão perdida ou encerramento)
                    break

                # Verifica o hash do arquivo recebido
                if verify_hash(file_data, hash_value):
                    # Salva o arquivo na pasta do cliente
                    with open(DIR_CLIENT + filename, 'wb') as file:
                        file.write(file_data)
                    print(f"File '{filename}' received successfully and saved to '{DIR_CLIENT}'.")
                else:
                    print("ERROR: Hash verification failed. File may be corrupted.")

            # Erros do servidor
            elif status == Status.NOT_FOUND:
                print("ERROR: File not found on server.")
            elif status == Status.FILE_TOO_LARGE:
                print("ERROR: File too large to be sent by server.")
            elif status == Status.HEADER_TOO_LARGE:
                print("ERROR: Header too large to be processed.")
            elif status == Status.BAD_REQUEST:
                print("ERROR: Bad request sent to server.")
            else:
                print("ERROR: Unknown response from server.")
        
        # Seta o sinal de encerramento ao sair do loop
        self.shutdown_event.set()

        # Fecha o socket
        try:
            try:
                addr = self.tcp_socket.getpeername()
            except Exception:
                addr = None
            self.close_socket(self.tcp_socket, addr)
        except Exception:
            pass

    def parse_response(self, data):
        """
        Parseia a resposta do servidor.
        Formato esperado da mensagem de chat: "CHAT <msg_len>(2) <msg>"
        Formato esperado do header do arquivo: status(1) | filename_len(2) | filename | file_size(8) | hash_len(2) | hash
        """
        try:
            text = data.decode('utf-8')     # Tenta decodificar como texto
        except UnicodeDecodeError:
            text = ""

        if text.startswith(Commands.CHAT):  # Mensagem de chat
            try:
                message_len = int(text.split(' ', 2)[1])
                message = text.split(' ', 2)[2]
                return Commands.CHAT, (message_len, message)
            except IndexError:
                return None, None

        # Resposta de arquivo
        try:
            status = int.from_bytes(data[:1], 'big')   # Extrai o status da resposta
        except (IndexError, ValueError):
            return None, None
        
        if status != Status.OK:
            return status, None
        try:
            # Extrai os dados do arquivo
            filename_len = int.from_bytes(data[1:3], 'big')
            filename = data[3:3+filename_len].decode('utf-8')
            file_size = int.from_bytes(data[3+filename_len:11+filename_len], 'big')
            hash_len = int.from_bytes(data[11+filename_len:13+filename_len], 'big')
            hash_value = data[13+filename_len:13+filename_len+hash_len]
            file_data = data[13+filename_len+hash_len:]
            return status, (filename, file_size, hash_value, file_data)
        except (IndexError, ValueError, UnicodeDecodeError):
            return None, None
    
if __name__ == "__main__":
    ip = input("Enter server IP (default: localhost): ")
    if not ip:
        ip = "localhost"
    port = input("Enter server port (default: 12345): ")
    if not port:
        port = 12345
    client = Client(ip, port)