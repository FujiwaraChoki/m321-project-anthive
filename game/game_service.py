import json
import random
import selectors
import socket
import traceback

from ant import Ant
from hive import Hive
from message.client_message import ClientMessage

GAME_HOST = "127.0.0.1"
GAME_PORT = 61112
DISCOVERY_HOST = "127.0.0.1"
DISCOVERY_PORT = 61111
NUM_ANTS = 3
NUM_ROUNDS = 5
DEBUG = True


def main():
    hives = init_game()
    for i in range(NUM_ROUNDS):
        play_round(hives)

    for hive in hives:
        quit_game(hive, "Game over")


def init_game() -> list:
    """
    initializes a new game
    :return:
    """
    hives = create_hives()
    create_world(hives)
    num_ants = NUM_ANTS
    for hive in hives:
        for count in range(num_ants):
            ant = Ant(xcoord=hive.xcoord, ycoord=hive.ycoord, food=0)
            hive.ants.append(ant)
    return hives


def create_hives() -> list:
    """
    queries all hive services and creates the hives
    :return:
    """
    action = {"action": "query", "type": "hive"}
    host = DISCOVERY_HOST
    port = DISCOVERY_PORT
    message = send_request(action, host, port)
    hive_list = json.loads(message.response)
    hives = []
    for item in hive_list:
        hive = Hive(ipaddr=item["ip"], port=item["port"], foodstore=0, ants=[])
        hives.append(hive)
    return hives


def create_world(hives) -> None:
    """
    creates the world and places the hives
    :param hives:
    :return:
    """

    """ Not used in gametest
    action = {'action': 'query', 'type': 'world'}
    host =DISCOVERY_HOST
    port = DISCOVERY_PORT
    message = send_request(action, host, port)
    print(message)
    """
    positions = [1, 1, 1, 9, 9, 9, 9, 1]  # positions for 4 hives
    ix = 0
    for hive in hives:
        hive.xcoord = positions[ix]
        hive.ycoord = positions[ix + 1]
        ix += 2


def play_round(hives):
    """
    plays one round of the game
    :param hives:
    :return:
    """
    field_types = ["water", "empty", "home", "hill", "friend", "foe", "food"]
    for hive in hives:
        num_ants = random.randint(1, 5)
        hive_data = {"action": "round", "count": num_ants, "ants": []}
        for i in range(num_ants):
            ant_data = {
                "xcoord": random.randint(-99, 99),
                "ycoord": random.randint(-99, 99),
                "food": random.randint(0, 1),
                "area": random.choices(field_types, k=25),
            }
            hive_data["ants"].append(ant_data)

        try:
            message = send_request(hive_data, hive.ipaddr, hive.port)
            if DEBUG:
                print(f"Game_Service/play_round: response={message.response}")
            moves = json.loads(message.response)
            if len(moves) != num_ants:
                quit_game(
                    hive,
                    f"Number of moves {len(moves)} does not match the number of ants {num_ants}",
                )
                hives.remove(hive)
                return
            directions = ["N", "NW", "W", "SW", "S", "SE", "E", "NE", "H"]
            if not set(moves).issubset(directions):
                quit_game(hive, f"One or more moves are illegal")
                hives.remove(hive)
                return
        except Exception:
            raise Exception


def quit_game(hive, reason):
    action = {"action": "quit", "reason": reason}
    message = send_request(action, hive.ipaddr, hive.port)
    if DEBUG:
        print(f"Game_Service/play_round: message={message}")


def send_request(action, host, port):
    """
    sends a request to the server
    :param action:
    :return:
    """

    sel = selectors.DefaultSelector()
    request = create_request(action)
    start_connection(sel, host, port, request)
    message = None
    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        f"Main: Error: Exception for {message.ipaddr}:\n"
                        f"{traceback.format_exc()}"
                    )
                    message.close()
            # Check for a socket being monitored to continue.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()
    return message


def process_response(action, message):
    """
    process the response from the server
    :param action:
    :param message:
    :return:
    """
    pass


def create_request(action_item):
    """
    creates the request to send
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
    starts the connection to the remote socket
    :param sel:
    :param host:
    :param port:
    :param request:
    :return:
    """
    addr = (host, port)
    if DEBUG:
        print(f"Game_Service: Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = ClientMessage(sel, sock, addr, request)
    sel.register(sock, events, data=message)


if __name__ == "__main__":
    main()
