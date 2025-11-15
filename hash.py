import hashlib

def calc_hash(data, algorithm='sha256'):
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.digest()

def verify_hash(data, hash, algorithm='sha256'):
    return calc_hash(data, algorithm) == hash

def encapsulate(data):
    if isinstance(data, str):
        data.encode("utf-8")
    hash = calc_hash(data)
    return hash + data

def get_hash_msg(data):
    return data[:32], data[32:]