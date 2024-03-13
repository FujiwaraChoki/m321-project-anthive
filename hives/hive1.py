import selectors
import socket

from message.client_message import ClientMessage
from message.server_message import ServerMessage

ANTHILL_HOST = "127.0.0.1"
ANTHILL_PORT = 62123  # TODO 62000 - 62999
DISCOVERY_HOST = "127.0.0.1"
DISCOVERY_PORT = 61111
DEBUG = True


def main():
    register()
    game()


def register():
    """
    register this anthill service with the discovery service
    :return: None
    """
    sel = selectors.DefaultSelector()
    start_connection(
        sel,
        DISCOVERY_HOST,
        DISCOVERY_PORT,
        create_request(
            dict(
                action="register",
                service="anthill",
                host=ANTHILL_HOST,
                port=ANTHILL_PORT,
            )
        ),
    )
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            message.process_events(mask)
        if not sel.get_map():
            break
    sel.close()


def game():
    """
    process the rounds of the game
    :return:
    """
    sel = selectors.DefaultSelector()
    start_connection(
        sel,
        ANTHILL_HOST,
        ANTHILL_PORT,
        create_request(
            dict(
                action="start",
            )
        ),
    )
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            message.process_events(mask)
        if not sel.get_map():
            break
    sel.close()


def process_action(message):
    """
    process the action from the game service
    :param message:
    :return:
    """
    if DEBUG:
        print(f"Hive1: Processing action {message.data}")
    if message.data["action"] == "end":
        message.close()
    else:
        message.send(create_request(dict(action="move", direction="north")))


def create_request(action_item):
    """
    creates the body of the request
    :param action_item:
    :return:
    """
    return dict(
        type="text/json",
        encoding="utf-8",
        content=action_item,
    )


def start_connection(sel, host, port, request):
    """
    starts the connection to a remote socket
    :param sel:
    :param host:
    :param port:
    :param request:
    :return:
    """
    addr = (host, port)
    if DEBUG:
        print(f"Hive1: Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = ClientMessage(sel, sock, addr, request)
    sel.register(sock, events, data=message)


def accept_wrapper(sel, sock):
    """
    Wrapper for the recieved messages
    :param sel:
    :param sock:
    :return:
    """
    conn, addr = sock.accept()  # Should be ready to read
    if DEBUG:
        print(f"Hive1: Accepted connection from {addr}")
    conn.setblocking(False)
    message = ServerMessage(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)


if __name__ == "__main__":
    main()
