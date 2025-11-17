BUFF_SIZE = 1024
DIR_SERVER = "server_files/"
DIR_CLIENT = "client_files/"

class Commands:
    EXIT = "EXIT"
    GET_FILE = "GET_FILE"

class Status:
    OK = 0
    BAD_REQUEST = 1
    NOT_FOUND = 2
    HEADER_TOO_LARGE = 3