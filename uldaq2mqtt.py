import threading
from uldaq import (get_daq_device_inventory,
                   DaqDevice,
                   InterfaceType,
                   DigitalDirection,
                   DigitalPortType)
from enum import Flag, auto
import argparse
import time
import paho.mqtt.client as mqtt

interfaceType = InterfaceType.USB

class Bits(Flag):
    ONE = auto()
    TWO = auto()
    THREE = auto()
    FOUR = auto()
    FIVE = auto()
    SIX = auto()
    SEVEN = auto()
    EIGHT = auto()

class DeviceClient(object):
    
    def __init__(self):
        self.__lastInputAction = {
            0: {
                Bits.ONE: False,
                Bits.TWO: False,
                Bits.THREE: False,
                Bits.FOUR: False,
                Bits.FIVE: False,
                Bits.SIX: False,
                Bits.SEVEN: False,
                Bits.EIGHT: False,
            },
            1: {
                Bits.ONE: False,
                Bits.TWO: False,
                Bits.THREE: False,
                Bits.FOUR: False,
                Bits.FIVE: False,
                Bits.SIX: False,
                Bits.SEVEN: False,
                Bits.EIGHT: False,
            },
            2: {
                Bits.ONE: False,
                Bits.TWO: False,
                Bits.THREE: False,
                Bits.FOUR: False,
                Bits.FIVE: False,
                Bits.SIX: False,
                Bits.SEVEN: False,
                Bits.EIGHT: False,
            }
        }

    def connect(self, device_id, mqttClient):
        self.__daq_device = None
        self.__device_id = device_id
        self.__mqttClient = mqttClient

        try:
            # Get descriptors for all of the available DAQ devices.
            self.__devices = get_daq_device_inventory(interfaceType)
            self.__number_of_devices = len(self.__devices)
            if self.__number_of_devices == 0:
                raise Exception('Error: No DAQ devices found')

            # Create the DAQ device object
            # associated with the specified descriptor index.
            self.__device = next(
                f for f in self.__devices if f.unique_id == self.__device_id)

            print('Trying to connect to Device Id: ', self.__device_id)
            self.__daq_device = DaqDevice(self.__device)

            # Get the DioDevice object and verify that it is valid.
            self.__dio_device = self.__daq_device.get_dio_device()
            if self.__dio_device is None:
                raise Exception(
                    'Error: The DAQ device does not support digital input')

            # Establish a connection to the DAQ device.
            self.__descriptor = self.__daq_device.get_descriptor()
            print('Connecting to', self.__descriptor.dev_string)
            self.__daq_device.connect()

            # Get the port types for the device(AUXPORT, FIRSTPORTA, ...)
            dio_info = self.__dio_device.get_info()
            port_types = dio_info.get_port_types()

            # Configure the entire port for input.
            for portType in port_types:
                self.__dio_device.d_config_port(
                    portType, DigitalDirection.INPUT)

        except Exception as e:
            print('\n', e)
            self._disconnect()
            raise Exception(e)

    def read_device(self):
        try:
            res = self.__dio_device.d_in_list(
                DigitalPortType.FIRSTPORTA, DigitalPortType.FIRSTPORTC)

            for i, port in enumerate(res):
                bits = Bits(~port)
                self.__update_input(i, bits)

        except Exception as e:
            print('\n', e)
            self._disconnect()
            raise Exception(e)

    def _disconnect(self):
        try:
            if self.__daq_device:
                if self.__daq_device.is_connected():
                    self.__daq_device.disconnect()
                self.__daq_device.release()
        except Exception as e:
            print('\n', e)
            raise Exception(e)

    def __update_input(self, port, bits):
        for bit in Bits:
            pressed = bit in bits
            if (self.__lastInputAction[port][bit] != pressed):
                self.__lastInputAction[port][bit] = pressed
                self.__publish(port, bit, pressed)

    def __publish(self, port, bit, pressed):
        self.__mqttClient.publish(self.__device_id, str(port) + "/" + str(bit), pressed)


class DeviceThread(threading.Thread):
    def __init__(self):
        self.__deviceClient = DeviceClient()
        self.stop = False
        super(DeviceThread, self).__init__()

    def connect(self, device_id, mqttClient):
        self.__deviceClient.connect(device_id, mqttClient)

    def disconnect(self):
        self.__deviceClient._disconnect()

    def run(self):
        try:
            while True:
                if self.stop:
                    break

                self.__deviceClient.read_device()
        finally:
            self.disconnect()

class MqttClient:
    
    def __init__(self, ip, port):
        self.__client = mqtt.Client()
        self.__client.on_connect = self.__on_connect
        self.__client.connect(ip, port, 60)
        self.__client.loop_start()

    def __enter__(self):
        return self

    # ...

    def __exit__(self, exc_type, exc_value, traceback):
        self.__client.loop_stop()
        self.__client.disconnect()
        print("Disconnected")

    def publish(self, device, port, message):
        self.__client.publish("uldaq2mqtt/" + device + "/" + port, message)
        print("uldaq2mqtt/" + device + "/" + port + " --- Message: " + message)

    # The callback for when the client receives a CONNACK response from the server.

    def __on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # client.subscribe("$SYS/#")

def check_thread_alive(thr):
    thr.join(timeout=0.0)
    return thr.is_alive()

def main():
    devices = get_daq_device_inventory(InterfaceType.ANY)
    if not devices:
        raise Exception('Error: No DAQ devices found')

    print('Found', len(devices), 'DAQ device(s):')
    for device in devices:
        print('  ', device.product_name, ' (', device.unique_id, ') - ',
              'Device ID = ', device.product_id, sep='')

    parser = argparse.ArgumentParser(description='Device Id(s).')
    parser.add_argument('devices', metavar='D', type=str, nargs='+',
                        help='a list of device Ids')
    parser.add_argument('--mqtt-ip', dest='mqttIp', type=str, default="127.0.0.1",
                    help='The IP address of the MQTT Server')
    parser.add_argument('--mqtt-port', dest='mqttPort', type=int, default=1883,
                    help='The port number of the MQTT Server')

    args = parser.parse_args()
    threads = []
    mqttClient = MqttClient(args.mqttIp, args.mqttPort)

    for device in args.devices:
        try:
            thread = DeviceThread()
            thread.connect(device, mqttClient)
            thread.start()
            threads.append(thread)
        except Exception as e:
            for thread in threads:
                thread.stop = True
            raise Exception(e)

    while True:
        for thread in threads:
            if not check_thread_alive(thread):
                for thread in threads:
                    thread.stop = True
                raise Exception("Thread died.")
                
        time.sleep(1)


if __name__ == "__main__":
    main()