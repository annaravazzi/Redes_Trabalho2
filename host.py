"""
Módulo host base para comunicação TCP.
Superclasse para Cliente e Servidor.
"""

import socket
from macros import MAX_BUFF_SIZE

class Host():
    def __init__(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # Cria socket TCP
        self.tcp_socket.settimeout(1.0)     # Timeout (para verificar encerramento do programa)

    def close_socket(self, sock, addr):
        """
        Fecha o socket dado.
        """
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
            if addr:
                print(f"Socket {addr} closed.")
        except OSError:
            pass

    def send_message(self, sock, message):
        """
        Envia a mensagem pelo socket dado.
        """
        try:
            if isinstance(message, int):
                message = message.to_bytes(1, 'big')
            elif isinstance(message, str):
                message = message.encode('utf-8')
        except Exception:
            return

        try:
            sock.sendall(message)
        except (ConnectionResetError, BrokenPipeError):
            raise ConnectionError
        except OSError as e:
            if e.winerror == 10038:  # Socket já fechado
                return
    
    def receive_message(self, sock, buffer_size=MAX_BUFF_SIZE):
        """
        Recebe uma mensagem pelo socket dado.
        """
        try:
            data = sock.recv(buffer_size)
            if not data:    # Conexão fechada
                return None
            return data
        except (ConnectionResetError, BrokenPipeError):
            return None
        except socket.timeout:
            return "TIMEOUT"
        except OSError as e:
            if e.winerror == 10038:  # Socket já fechado
                return None
            