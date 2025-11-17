"""
Pequena biblioteca para cálculo e verificação de hashes (SHA256).
"""

import hashlib

def calc_hash(data, algorithm='sha256'):
    """
    Calcula o hash dos dados fornecidos (bytes) usando o algoritmo especificado.
    Retorna o hash em bytes.
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.digest()

def verify_hash(data, hash, algorithm='sha256'):
    """
    Verifica se o hash dos dados fornecidos corresponde ao hash fornecido.
    """
    return calc_hash(data, algorithm) == hash

def get_hash_msg(data):
    """
    Separa o hash (primeiros 32 bytes) da mensagem nos dados encapsulados (em bytes).
    """
    # return data[:32], data[32:]