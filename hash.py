"""
Pequena biblioteca para cálculo e verificação de hashes (SHA256).
"""

import hashlib
from macros import HASH_ALGORITHM

def calc_hash(data, algorithm=HASH_ALGORITHM):
    """
    Calcula o hash dos dados fornecidos (bytes) usando o algoritmo especificado.
    Retorna o hash em bytes.
    """
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.digest()

def verify_hash(data, hash, algorithm=HASH_ALGORITHM):
    """
    Verifica se o hash dos dados fornecidos corresponde ao hash fornecido.
    """
    return calc_hash(data, algorithm) == hash