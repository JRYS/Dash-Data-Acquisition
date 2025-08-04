import sys
import json
import socket
import threading
from time import time, sleep
import ctypes
import struct
import logging
import logging.config
from getBoard import BOARDS
from collections import namedtuple

from ctypes import cast, POINTER, c_double, c_ushort
from mcculw import ul
from mcculw.enums import ScanOptions, FunctionType, Status
from mcculw.enums import ULRange


def get_msg(conn, typ):
    """
    receive message: gets message length then message
    user must provide type of expected message
    typ: (str, int, list)
    """

    # receive message length
    recv_str = conn.recv(ctypes.sizeof(ctypes.c_uint))
    unpacked_tuple = struct.unpack('<' + 'I', recv_str)
    msg = list(unpacked_tuple)
    retErr = 0
    match typ:
        case 'int':
            item = msg[0]
            return item
        case 'list':
            bytes_to_recv = msg[0]
            s = conn.recv(bytes_to_recv)
            item = json.loads(s.decode('utf-8'))
            return item
        case 'str':
            bytes_to_recv= msg[0]
            s = conn.recv(bytes_to_recv)
            return s
        case _:
            retErr = -1
    return retErr


def send_msg(conn, itm):
    """
    Send message: sends length of message then message
    conn (socket)
    ite: can be str, int or list
    """

    retErr = 0
    if type(itm) is str and itm is not None:
        packed_data = struct.pack('<' + 'I', len(itm))
        conn.sendall(packed_data)
        conn.sendall(itm.encode('utf-8'))
    elif type(itm) is int and itm is not None:
        packed_data = struct.pack('<' + 'I', itm)
        conn.sendall(packed_data)
    elif type(itm) is list and itm is not None:
        json_string = json.dumps(itm)
        packed_data = struct.pack('<' + 'I', len(json_string))
        conn.sendall(packed_data)
        conn.sendall(json_string.encode('utf-8'))
    else:
        retErr = -1
    return retErr


def read_device_scans(config, flag, conn):
    """
    This thread function is responsible
    for programming the device and returning data to the
    client. Because ScaleData scan option is used,
    the data type is a double (8 bytes). The struct
    module is used to pack the values into a string
    to be sent to client application.

    :param config: (namedTuple) contains configuration info
    :param flag: (thread event flag) used to kill the thread
    :param conn: (socket handle)
    :return: N/A
    """
    logger = logging.getLogger('serverInfo')
    board_number = config.Board
    logger.info(f'Board number: {config.Board}')
    logger.info(f'Board descriptor: {config.Descriptor}')

    number_of_channels = len(config.Channels)
    sample_rate = config.Rate

    # size the buffer to be a multiple of 32.
    # For insurance, I sized to  hold 10 seconds of data
    one_second = sample_rate * number_of_channels
    buffer_size = (one_second - (one_second % 96)) * 10

    memHandle = ul.scaled_win_buf_alloc(buffer_size)

    if memHandle is None:
        print("memory allocation error")
        return

    try:

        # set channel order
        ul.a_load_queue(board_number,
                        config.Channels,
                        config.Ranges,
                        number_of_channels)

        opts = ScanOptions.SCALEDATA \
               | ScanOptions.CONTINUOUS \
               | ScanOptions.BACKGROUND

        actual_rate = ul.a_in_scan(board_number,
                                   0,
                                   3,
                                   buffer_size,
                                   sample_rate,
                                   ULRange.BIP10VOLTS,
                                   memHandle,
                                   opts)
        sleep(0.2)
        data = cast(memHandle, POINTER(c_double))
        samples = 0
        tail = 0
        while flag.is_set():
            '''
            This routine sends the buffered data to the client app. 
            I chose half the sample rate * number of channels, or 
            0.5 sec. as the minimum amount to send. 
            '''
            status, curr_count, head = ul.get_status(board_number,
                                                     FunctionType.AIFUNCTION)
            if head > tail:
                if (head - tail) > int(sample_rate * number_of_channels / 2):
                    sending = head - tail
                    samples = samples + sending
                    send_msg(conn, sending)

                    logger.info(f'Transferred {sending:6d}\tTotal Transferred {samples:12d}')

                    python_list = data[tail: head]
                    packed_data = struct.pack('<' + 'd' * len(python_list),
                                              *python_list)
                    conn.sendall(packed_data)
                    tail = head

            else:
                sending = buffer_size - tail + head
                if sending > int(sample_rate * number_of_channels / 2):
                    samples = samples + sending
                    send_msg(conn, sending)

                    logger.info(f'Transferred {sending:6d}\tTotal Transferred {samples:12d}')

                    python_list = data[tail:buffer_size] + data[0:head]
                    packed_data = struct.pack('<' + 'd' * len(python_list),
                                              *python_list)
                    conn.sendall(packed_data)
                    tail = head
            sleep(0.1)

        ul.stop_background(board_number, FunctionType.AIFUNCTION)
        if memHandle is not None:
            ul.win_buf_free(memHandle)
        ul.release_daq_device(board_number)
        logger.info(f'Board {board_number} closed.')
    except Exception as e:
        logger.info(e)


def handle_client(conn, addr):
    boards = BOARDS()
    board_number = -1
    board_desc = None
    thread = None
    stop_event = threading.Event()
    board_selected = False
    logger = logging.getLogger('serverInfo')
    while True:
        try:
            data = b""
            data = get_msg(conn, 'str')

            if not data:
                break  # Terminate the connection if no data is received
            message = data.decode().lower()
            logger.info(f"Received from {addr}: Command: {message}")

            match message:
                case 'list':

                    dlist = boards.read_boards()
                    send_msg(conn, dlist)

                case 'open':

                    try:
                        if board_selected is False:

                            board_number = get_msg(conn, 'int')
                            logger.info(f'Board number: {board_number}')

                            # Get board descriptor from UL discovered devices
                            board_desc = boards.read_dev_desc(board_number)
                            logger.info(board_desc.unique_id)
                            send_msg(conn, board_desc.unique_id)

                            # create device
                            ul.ignore_instacal()
                            ul.create_daq_device(board_number, board_desc)
                            board_selected = True

                        else:
                            logger.info(f'Board {board_number} is selected')
                    except Exception as e:
                        logger.info('Ah Snap\n', e)

                case 'start':

                    if board_selected is False:
                        logger.info('No device, run open_device')
                    else:

                        input_channels = get_msg(conn, 'list')
                        logger.info(f'Input Channels: {input_channels}')

                        input_ranges = get_msg(conn, 'list')
                        logger.info(f'Input Ranges: {input_ranges}')

                        sample_rate = get_msg(conn, 'int')
                        logger.info(f'Sample Rate: {sample_rate}')

                        samples_to_display = get_msg(conn, 'int')
                        logger.info(f'Samples to Display: {samples_to_display}')

                        Config = namedtuple('Config', ['Board',
                                                       'Descriptor',
                                                       'Channels',
                                                       'Ranges',
                                                       'Samples',
                                                       'Rate'])

                        configuration = Config(Board=board_number,
                                               Descriptor=board_desc,
                                               Channels=input_channels,
                                               Ranges=input_ranges,
                                               Samples=samples_to_display,
                                               Rate=sample_rate)

                        stop_event = threading.Event()
                        stop_event.set()  # set to True initially
                        thread = threading.Thread(target=read_device_scans,
                                                  args=(configuration,
                                                        stop_event,
                                                        conn))
                        thread.start()

                case 'stop':

                    if stop_event.is_set():
                        stop_event.clear()
                        thread.join()
                        thread = None

                    else:
                        ul.release_daq_device(board_number)
                        logger.info(f'Board {board_number} closed.')

                    board_selected = False

                case 'exit':
                    break

                case _:
                    logger.info(message)
        except TimeoutError:
            logger.info("Timeout occurred while receiving data.")
        except ConnectionResetError:
            logger.info(f"Client {addr} has disconnected.")
            break

    conn.close()
    logger.info(f"Connection with {addr} closed.")


def get_ip_address():
    """ Utility function to get the IP address of the device. """
    ip_address = '127.0.0.1'  # Default to localhost
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(('1.1.1.1', 1))  # Does not have to be reachable
        ip_address = sock.getsockname()[0]
    finally:
        sock.close()

    return ip_address


# Start the server
def start_server():

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': 'serverInfo.log',
                'formatter': 'default',
            },
            'stdout': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },
        'loggers': {
            'serverInfo': {
                'handlers': ['file', 'stdout'],
                'level': 'INFO',
                'propagate': True,
            },
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger('serverInfo')
    logger.info('Info message: serverInfo module loaded successfully.')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # HOST = get_ip_address()
        HOST = '127.0.0.1'
        PORT = 65432
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        logger.info(f"Server listening on {HOST}:{PORT}...")

        while True:
            conn, addr = server_socket.accept()  # Accept a client connection
            thread_count = threading.active_count() - 1
            if thread_count > 1:
                conn.close()    # two connections are normal (dash 0 & flask 1),
                                # to prevent distributing the running acquisition,
                                # shutdown any additional connections
            else:
                logger.info(f"Active connections: {thread_count}")
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.start()  # Start a new thread for each client


if __name__ == "__main__":
    start_server()
