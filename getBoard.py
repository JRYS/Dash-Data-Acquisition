from mcculw import ul
from mcculw.enums import InterfaceType
"""
Python class used to locate USB-200
series boards. InstaCal must be installed,
but you don't have to run it. 
"""

class BOARDS:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_device_list = []
        self.ul_list = []
        self.device_count = self._get_boards()

    def _valid_board(self, daq_type):
        """
        simple match statement to ensure the
        device is supported by using the device
        type that is unique to MCC devices

        :param daq_type: (int)
        :return: (boolean)
        """

        match daq_type:
            case 0x113:
                return True
            case 0x114:
                return True
            case 0x12B:
                return True
            case 0x12C:
                return True
            case _:
                return False

    def _get_boards(self):
        """
        This function uses the MCC Universal Library to
        interrogate the USB bus for MCC devices. In doing
        so, it creates two lists, one with all the found MCC
        devices, and another with just the one that make it
        through the _valid_board filter
        :return: (int) device count
        """
        board_index = 0
        ul.ignore_instacal()
        self.available_device_list = []
        self.ul_list = []
        device_count = 0
        self.ul_list = ul.get_daq_device_inventory(InterfaceType.USB)
        if len(self.ul_list) > 0:
            for device in self.ul_list:
                device_dict = {
                    "Name": str(device),
                    "Product_ID": device.product_id,
                    "Serial_Number": device.unique_id,
                    "Board_Number": board_index
                }
                if self._valid_board(device.product_id) is True:
                    self.available_device_list.append(device_dict)
                    device_count += 1
                board_index = board_index + 1
        else:
            print("No devices detected")
        return device_count


    def read_boards(self):
        """
        returns the available device list
        :return: (list)
        """
        return self.available_device_list

    def read_dev_desc(self, board_num):
        """
        returns the device descriptor
        associated with board_number
        :param board_num:
        :return: descriptor
        """
        return self.ul_list[int(board_num)]
