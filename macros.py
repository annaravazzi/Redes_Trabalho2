class Commands:
    EXIT = "EXIT"
    GET_FILE = "GET_FILE"
    CHAT = "CHAT"
    WRONG_COMMAND = "WRONG_COMMAND"

class Status:
    OK = 0
    BAD_REQUEST = 1
    NOT_FOUND = 2
    HEADER_TOO_LARGE = 3
    FILE_TOO_LARGE = 4

MAX_BUFF_SIZE = 4096
DIR_SERVER = "server_files/"
DIR_CLIENT = "client_files/"
HASH_ALGORITHM = 'sha256'