import socket
from host import Host
import threading
from macros import MAX_BUFF_SIZE, DIR_SERVER, Commands, Status
from hash import calc_hash

class Server(Host):
    def __init__(self, IP, port):
        super().__init__()
        self.tcp_socket.bind((IP, port)) 
        self.tcp_socket.listen()
        print(f"Server listening on {IP}:{port}")
        print("Type messages to broadcast to all clients or to a specific (ip:port).")
        print("Press Ctrl+C to stop the server.")

        # Mantém registro dos clientes conectados: mapeia socket -> endereço
        self.clients = {}
        # Mapeia socket -> Thread para fazer join nos threads de cliente
        self.client_threads = {}
        # Trava o acesso à lista compartilhada de clientes conectados
        self.clients_lock = threading.Lock()

        # Evento de encerramento
        self.server_shutdown_event = threading.Event()

        # Inicia a thread de aceitação de clientes para que a thread principal possa ser usada para entradas do console
        self.acceptor_thread = threading.Thread(target=self.execute_acceptor, daemon=False)
        self.acceptor_thread.start()

        # Loop do console do servidor na thread principal para permitir o broadcast de mensagens de chat
        self.server_console_loop()

    def server_console_loop(self):
        """
        Loop do console do servidor para enviar mensagens de chat a todos os clientes.
        Roda na thread principal.
        """
        try:
            while True:
                line = input()  # Lê entrada do console
                if not line:
                    continue
                try:
                    # Extrai endereço do remetente (opcional)
                    addr = line.split(' ', 1)[0].replace('(', '').replace(')', '')
                    ip = addr.split(':')[0]
                    port = int(addr.split(':')[1])
                    line = line.split(' ', 1)[1]
                except (IndexError, ValueError):
                    ip = None
                    port = None
                msg = f"{Commands.CHAT} {str(len(line))} {line}"

                # Envia mensagem de chat para todos os clientes ou para um cliente específico
                self.broadcast_message(msg, (ip, port) if ip and port else None)

        # Permite o encerramento do servidor com Ctrl+C
        except KeyboardInterrupt:
            print("Closing server...")
            try:
                self.initiate_shutdown()
            except Exception:
                # Fallback em caso de erro no shutdown cooperativo
                self.server_shutdown_event.set()
                try:
                    self.close_all_clients()
                except Exception:
                    pass
                try:
                    self.close_socket(self.tcp_socket, self.tcp_socket.getsockname())
                except Exception:
                    pass
            print("Server closed.")

    def execute_acceptor(self):
        """
        Loop que aceita conexões de clientes e inicia uma thread para cada cliente.
        (executa em uma thread em segundo plano)
        """
        while True:
            # Checa se o servidor será encerrado
            if self.server_shutdown_event.is_set():
                return
            try:
                client_socket, client_address = self.tcp_socket.accept()     # Cria socket para o cliente
            except socket.timeout:
                continue
            except OSError:
                # Servidor continua on
                continue

            print(f"Connection established with {client_address}")
            # Adiciona o cliente à lista de clientes conectados
            with self.clients_lock:
                self.clients[client_socket] = client_address
            # Inicia uma thread para tratar a comunicação com o cliente e armazena a thread
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address), daemon=False)
            with self.clients_lock:
                self.client_threads[client_socket] = client_thread
            client_thread.start()
        
    
    def handle_client(self, client_socket, client_address):  
        """
        Trata a comunicação com o cliente.
        """
        while True:
            # Checa se o servidor será encerrado
            if self.server_shutdown_event.is_set():
                break

            msg = self.receive_message(client_socket)
            if msg is None:     # Cliente desconectou
                break
            if msg == "TIMEOUT":
                continue

            try:
                command = msg.decode('utf-8').split(' ', 1)[0]  # Extrai comando da mensagem
            except (UnicodeDecodeError, IndexError):
                try:
                    self.send_message(client_socket, client_address, Status.BAD_REQUEST)
                except ConnectionError:
                    break
                print(f"ERROR: Unable to decode client message from {client_address}.")
                continue

            if command == Commands.EXIT:    # Cliente deseja desconectar
                print(f"Client {client_address} requested to disconnect.")
                break

            elif command == Commands.GET_FILE:  # Cliente solicita um arquivo
                try:
                    filename = msg.decode('utf-8').split(' ')[1]
                    print(f"Client {client_address} requested file: {filename}")
                    self.send_file(client_socket, filename)     # Envia o arquivo solicitado
                except (UnicodeDecodeError, IndexError):
                    try:
                        self.send_message(client_socket, client_address, Status.BAD_REQUEST)
                    except ConnectionError:
                        break
                    print(f"ERROR: Unable to parse filename from client request ({client_address}).")
                    continue
                except ConnectionError:
                    break

            elif command == Commands.CHAT:  # Mensagem de chat
                try:
                    # Parsing do request
                    message_len = msg.decode('utf-8').split(' ', 2)[1]
                    message = msg.decode('utf-8').split(' ', 2)[2]
                except (UnicodeDecodeError, IndexError):
                    try:
                        self.send_message(client_socket, client_address, Status.BAD_REQUEST)
                    except ConnectionError:
                        break
                    print(f"ERROR: Unable to decode chat message from {client_address}.")
                    continue
                try:
                    while len(message) < int(message_len):
                        if self.server_shutdown_event.is_set():
                            raise Exception
                        remaining = self.receive_message(client_socket, client_address, int(message_len) - len(message))
                        if remaining is None:
                            raise Exception
                        if remaining == "TIMEOUT":
                            continue
                        message += remaining.decode('utf-8')
                except Exception:
                    break

                # Mostra mensagem no console do servidor
                print(f"[CLIENT] {client_address}: {message}")
            
            else:   # Comando desconhecido
                try:
                    self.send_message(client_socket, Status.BAD_REQUEST)
                except ConnectionError:
                    break
                print(f"ERROR: Unknown command from client {client_address}.")

        # Fecha o socket do cliente ao sair do loop
        self.close_client(client_socket)

    def load_file(self, filename):
        """
        Carrega o arquivo solicitado do sistema de arquivos.
        Retorna o status e uma tupla com os dados do arquivo, tamanho e hash.
        """
        try:
            with open(DIR_SERVER + filename, 'rb') as file:
                f = file.read()
                return Status.OK, (f, len(f), calc_hash(f))
        except FileNotFoundError:
            return Status.NOT_FOUND, None
        except MemoryError:
            return Status.FILE_TOO_LARGE, None
        except Exception as e:
            print(f"ERROR: Exception while loading file {filename}: {e}")
            return Status.BAD_REQUEST, None
    
    def send_file(self, client_socket, filename):
        """
        Envia o arquivo solicitado ao cliente.
        Formato do header:
        status(1) + filename_len(2) + filename + file_size(8) + hash_len(2) + hash(32)
        """
        # Carrega o arquivo
        status, file_info = self.load_file(filename)

        # Trata erros ao carregar o arquivo
        if status == Status.FILE_TOO_LARGE:
            self.send_message(client_socket, Status.FILE_TOO_LARGE)
            print(f"ERROR: File {filename} is too large to load.")
            return
        elif status == Status.NOT_FOUND:
            self.send_message(client_socket, Status.NOT_FOUND)
            print(f"ERROR: File {filename} not found.")
            return
        elif status == Status.BAD_REQUEST or file_info is None:
            self.send_message(client_socket, Status.BAD_REQUEST)
            print(f"ERROR: Unable to load file {filename}.")
            return

        # Prepara os dados do arquivo
        file_data, file_size, hash_value = file_info

        # Header
        try:
            status = Status.OK.to_bytes(1, 'big')
            filename_bytes = filename.encode('utf-8')
            filename_len = len(filename_bytes).to_bytes(2, 'big')
            file_size_bytes = file_size.to_bytes(8, 'big')
            hash_len = len(hash_value).to_bytes(2, 'big')
        except OverflowError:
            self.send_message(client_socket, Status.HEADER_TOO_LARGE)
            print(f"ERROR: Header too large to send.")
            return

        # Monta o header completo
        header = status + filename_len + filename_bytes + file_size_bytes + hash_len + hash_value
        if len(header) > MAX_BUFF_SIZE:     # Header muito grande
            self.send_message(client_socket, Status.HEADER_TOO_LARGE)
            print("ERROR: Header too large to send.")
            return
        
        self.send_message(client_socket, header + file_data)
        
    def broadcast_message(self, message, specific_addr=None):
        """
        Manda uma mensagem de chat para todos os clientes conectados. Opcionalmente envia para um cliente específico.
        """
        with self.clients_lock:
            for sock in list(self.clients.keys()):
                if specific_addr and self.clients[sock] != specific_addr:
                    continue
                try:
                    self.send_message(sock, message)
                except ConnectionError:
                    self.close_client(sock)

    def close_client(self, client_socket):
        """
        Fecha o socket do cliente fornecido e o remove da lista de clientes conectados.
        """
        # Remove os clientes das listas
        with self.clients_lock:
            addr = self.clients.pop(client_socket, None)
            thread = self.client_threads.pop(client_socket, None)

        try:
            self.close_socket(client_socket, addr)
        except Exception:
            pass

        # Aguarda o término da thread de cliente
        try:
            if thread.is_alive():
                if threading.current_thread() is not thread:
                    thread.join(timeout=2.0)
        except Exception:
            pass

    def close_all_clients(self):
        """
        Fecha todos os sockets dos clientes conectados.
        """
        for sock in list(self.clients.keys()):
            try:
                self.close_client(sock)
            except Exception:
                pass

    def initiate_shutdown(self):
        """
        Inicia o shutdown cooperativo do servidor.
        """
        print("Initiating server shutdown...")
        self.server_shutdown_event.set()

        # Fecha o socket do servidor
        try:
            self.close_socket(self.tcp_socket, self.tcp_socket.getsockname())
        except Exception:
            pass

        # Fecha todos os clientes e junta threads
        with self.clients_lock:
            client_socks = list(self.clients.keys())
            threads = list(self.client_threads.values())

        for sock in client_socks:
            try:
                self.close_client(sock)
            except Exception:
                pass

        for t in threads:
            try:
                if t.is_alive():
                    t.join(timeout=2.0)
            except Exception:
                pass

        try:
            if self.acceptor_thread.is_alive():
                self.acceptor_thread.join(timeout=2.0)
        except Exception:
            pass

        print("Server shutdown complete.")

if __name__ == "__main__":
    server = Server("localhost", 12345)