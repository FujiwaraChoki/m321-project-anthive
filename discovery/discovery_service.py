import selectors
import socket
import traceback

from message.server_message import ServerMessage
from services import Services

HOST = "127.0.0.1"
PORT = 61111
DEBUG = True


def main():
    sel = selectors.DefaultSelector()
    services = Services()

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Avoid bind() exception: OSError: [Errno 48] Address already in use
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind((HOST, PORT))
    lsock.listen()
    print(f"Discovery: listening on {(HOST, PORT)}")
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)

    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(sel, key.fileobj)
                else:
                    message = key.data
                    print("HERE =>>>> ", key.data.request)
                    print("HERE 2 =>>>> ", key.data.event)
                    try:
                        message.process_events(mask)
                        process_action(message, services)
                    except Exception:
                        print(
                            f"Discovery: Error: Exception for {message.ipaddr}:\n"
                            f"{traceback.format_exc()}"
                        )
                        message.close()
    except KeyboardInterrupt:
        print("Discovery: Caught keyboard interrupt, exiting")
    finally:
        sel.close()


def process_action(message, services):
    if DEBUG:
        print(f"Discovery/process_action: event={message.event}")
    if message.event == "READ":
        action = message.request["action"]
        if action == "register":
            service_uuid = services.register(
                message.request["type"], message.request["ip"], message.request["port"]
            )
            message.response = service_uuid
        elif action == "heartbeat":
            result = services.heartbeat(message.request["uuid"])
            message.response = result
        elif action == "query":
            result = services.query(message.request["type"])
            message.response = result

        message.set_selector_events_mask("w")


def accept_wrapper(sel, sock):
    conn, addr = sock.accept()  # Should be ready to read
    if DEBUG:
        print(f"Discovery: Accepted connection from {addr}")
    conn.setblocking(False)
    message = ServerMessage(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)


if __name__ == "__main__":
    main()
