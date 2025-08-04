import socket
import json
import threading
import struct
import ctypes

thread = None
debug = True


class DaqSocketManager:
    """
    DaqSocketManager manages the socket communication
    to the server app that handles the complexities of
    the data acquisition.

    This was necessary because of the stateless design
    of the web browser application.
    """

    def __init__(self, host='127.0.0.1', port=65432):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None
        self.stop_event = threading.Event()
        self.data_list = []
        self.new_data = False
        self.rate = 1000
        self.samples_to_display = 1000
        self.channels = [0, 1, 2, 3]
        self.gains = [1, 1, 1, 1]

    def get_status(self):
        """
        returns the new data flat indicating
        it is safe toe fetch a block of data.
        :return: boolean
        """
        return self.new_data

    def get_data_list(self):
        """
        returns the list of available USB devices
        found on the system. It sets the new data flag
        false to ensure repeated data won't happen
        :return:
        """
        self.new_data = False
        return self.data_list

    def __iter__(self):
        return iter(self.get_data_list())

    def set_rate(self, update_rate):
        """
        :param update_rate:
        :return:
        """
        self.rate = update_rate

    def get_rate(self):
        """
        returns the current sample rate setting
        :return:
        """
        return self.rate

    def set_samples(self, count):
        """
        Sets the current samples setting.
        :param count:
        :return:
        """
        self.samples_to_display = count

    def get_samples(self):
        """
        returns the current samples setting
        :return:
        """
        return self.samples_to_display

    def set_channels(self, inputs):
        """
        Specifies the desired input channels
        to read during the acquisition

        Args:
             inputs (list): list of channel numbers
        """

        self.channels = inputs

    def get_channels(self):

        """
        used to read the input channels list used by
        the input channels

        Returns: list():
        """
        return self.channels

    def set_gains(self, ranges):
        """
        used to set the voltage range used by
        the input channels

        Args:
             ranges (list): list of input range enumerations
        """
        self.gains = ranges

    def get_gains(self):
        """
        used to read the input ranges used by
        the input channels

        Returns: list():
        """
        return self.gains

    def send_msg(self, itm):
        """
        Send message: sends length of message then message
        conn (socket)
        ite: can be str, int or list
        """
        retErr = 0
        if type(itm) is str and itm is not None:
            packed_data = struct.pack('<' + 'I', len(itm))
            self.socket.sendall(packed_data)
            self.socket.sendall(itm.encode('utf-8'))
        elif type(itm) is int and itm is not None:
            packed_data = struct.pack('<' + 'I', itm)
            self.socket.sendall(packed_data)
        elif type(itm) is list and itm is not None:
            json_string = json.dumps(itm)
            packed_data = struct.pack('<' + 'I', len(json_string))
            self.socket.sendall(packed_data)
            self.socket.sendall(json_string.encode('utf-8'))
        else:
            retErr = -1
        return retErr

    def get_msg(self, typ):
        """
        receive message: gets message length then message
        """
        # receive message length
        recv_str = self.socket.recv(ctypes.sizeof(ctypes.c_uint))
        unpacked_tuple = struct.unpack('<' + 'I', recv_str)
        msg = list(unpacked_tuple)
        retErr = 0
        match typ:
            case 'int':
                item = msg[0]
                return item
            case 'list':
                bytes_to_recv = msg[0]
                s = self.socket.recv(bytes_to_recv)
                item = json.loads(s.decode('utf-8'))
                return item
            case 'str':
                bytes_to_recv = msg[0]
                s = self.socket.recv(bytes_to_recv)
                return s
            case _:
                retErr = -1
        return retErr

    def disconnect(self):
        self.send_msg('exit')
        self.socket.close()
        self.socket = None

    def connect(self, host='127.0.0.1', port=65432):
        """
        Connect is used to establish a host/port socket address for
        other socket programs to use daqServer's functionality.

        Extra
        """

        if self.running is False:
            self.host = host
            self.port = port
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                if self.socket is None:
                    print('Whoops no socket')
                    return False
                self.socket.connect((self.host, self.port))
                self.socket.settimeout(2.0)
                print(f"Connected to {self.host}:{self.port}")
                return True

            except ConnectionResetError:
                print(f'Connection reset error.')
                print(f"Error connecting to server at {self.host}:{self.port}")
                print(f'Remote server in use.')
                self.socket = None
                exit(0)
            except ConnectionRefusedError:
                print(f"Error connecting to server at {self.host}:{self.port}")
                print("Please ensure server program is running.")
                self.socket = None
                exit(0)
        else:
            return False  # already in service

    def get_device_list(self):
        """
        returns a list of available USB-200 series
        devices in stall on the computer
        :return: (list)
        """
        try:
            self.send_msg('list')
            device_list = self.get_msg('list')
            return device_list
        except ConnectionResetError:
            print(f'Connection reset error.')
            print(f"Error connecting to server at {self.host}:{self.port}")
            print(f'Remote server in use.')
            self.socket = None
            exit(0)

    def open_list_device(self, board_number):
        """
        opens the USB device using only board number from the device list.
        board_number (int):

        """
        device_serial_number = 0
        try:
            # send open command
            self.send_msg('open')

            # send board number
            self.send_msg(int(board_number))

            device_serial_number = self.get_msg('str')
            return device_serial_number

        except TimeoutError:
            print("Open List Device: Timeout occurred opening device.")

        except ConnectionResetError:
            print(f'Connection reset error.')
            print(f"Error connecting to server at {self.host}:{self.port}")
            print(f'Remote server in use.')
            self.socket = None
            exit(0)

        finally:
            return device_serial_number

    def start_server(self):
        """
        This function sends the acquisition parameters and
        starts the thread function that fetches the server
        data.
        :return:
        """
        try:

            self.send_msg('start')

            self.send_msg(self.channels)

            self.send_msg(self.gains)

            self.send_msg(self.rate)

            self.send_msg(self.samples_to_display)

            self.stop_event = threading.Event()
            self.stop_event.set()

            nop = -1
            self.thread = threading.Thread(target=self.read_server_scans, args=(nop,))
            self.thread.start()

            self.running = True
            return 'running'

        except TimeoutError:
            print("Start Server: Timeout occurred stopping server.")
            return 'error'

        except ConnectionResetError:
            print(f'Start Server: Client {self.host} has disconnected.')
            return 'error'

    def stop_server(self):
        """
        This function stops the acquisition that is running
        in the server app. It also closes the device and
        free allocated memory.
        :return:
        """
        try:

            # self.send_string('stop')
            self.send_msg('stop')
            if self.running is True:
                # clear thread event flag
                self.stop_event.clear()  # stop the read scans thread
                self.thread.join()
            return 0

        except TimeoutError:
            print("Stop Server: Timeout occurred stopping server.")

        except ConnectionResetError:
            print(f"Stop Server: Client {self.host} has disconnected.")

        finally:
            self.running = False
            return 'idle'

    def read_server_scans(self, nop):
        """
        This function is run in a thread. It continuously
        catches the data sent by the server. There is no
        handshaking and instead, it calculates the amount of
        data the server will send it each time. Once a second,
        the server sends one second of data, which is the amount
        read_server_scans expects.
        :param nop: Not used
        :return: N/A
        """
        file_path = "web_daq_data.bin"
        try:
            size_of_double = ctypes.sizeof(ctypes.c_double)
            #with open(file_path, "wb") as file:

            while self.stop_event.is_set():

                # get number of samples to receive
                samples_to_read = self.get_msg('int')
                chunk_size = size_of_double * samples_to_read

                # read the samples
                recv_str = b""
                while len(recv_str) < chunk_size:
                    diff = min(chunk_size - len(recv_str), chunk_size)
                    chunk = self.socket.recv(diff)
                    recv_str += chunk
                #file.write(recv_str)
                l = (len(recv_str) // struct.calcsize('d'))
                unpacked_tuple = struct.unpack('<' + 'd' * l, recv_str)

                self.data_list = list(unpacked_tuple)
                self.new_data = True

            #with open(file_path, "rb") as file:
            #    binary_data = file.read()

            #l = (len(binary_data) // struct.calcsize('d'))
            #unpacked_tuple = struct.unpack('<' + 'd' * l, binary_data)
            #data = list(unpacked_tuple)
            #print(data[0:20])

            self.new_data = False
            return

        except TimeoutError:
            self.new_data = False
            return

        except ConnectionResetError:
            print(f"Read Server Scans: Client {self.host} has disconnected.")
