import socket
import threading
import time
import serial
import logging

class UartClient:
    def __init__(self, sever_host="/dev/ttyUSB0", server_port=9600):
        self.server_host = sever_host
        self.server_port = server_port
        self.serial_obj = serial.Serial(self.server_host, self.server_port, timeout=1)
        self.data_send = None
        self.data_recv = None
        self.setTorque = 0
        self.setSpd = 0
        self.spd = 0
        self.mode = "None"
        self.RunStatus = 0
        self.pulse = 0
        self.P = 0
        self.lastP = 0
    
    def server_handler(self):
        data = None
        while True:
            if self.serial_obj.in_waiting > 0:
                data = self.serial_obj.readline().decode("utf-8").strip()
            if not data:
                continue
            else:
                logging.info(f"{self.server_host} received: {data}")
                self.data_recv = data
                data = None
            # self.serial_obj.write(response.encode())
        
    def client_handler(self):
        while True:
            if self.data_send is not None:
                data = self.data_send
                self.data_send = None
                # print(f"Sending: {data}")
                self.serial_obj.write(data.encode())
            time.sleep(0.05)
    
    def start_threads(self):
        threading.Thread(target=self.server_handler, daemon=True).start()
        threading.Thread(target=self.client_handler, daemon=True).start()

if __name__ == "__main__":
    server_host1 = "/dev/ttyACM0"
    server_port1 = 9600
    server_host2 = "/dev/ttyACM1"
    server_port2 = 9600
    
    uart_client1 = UartClient(server_host1, server_port1)
    uart_client1.start_threads()
    uart_client2 = UartClient(server_host2, server_port2)
    uart_client2.start_threads()
    time.sleep(4)
    logging.basicConfig(level=logging.INFO)
    # data = input("Enter data to send: ")
    # uart_client1.data_send = data
    # uart_client2.data_send = data
    l_data1 = []
    l_data2 = []
    count = 0
    start_time = time.time()
    while True:
        if uart_client1.data_recv is not None:
            data1 = uart_client1.data_recv.split(",")
            l_data1.append(data1)
            print(f"List 1: {len(l_data1)}")
            uart_client1.data_recv = None
        if uart_client2.data_recv is not None:
            data2 = uart_client2.data_recv.split(",")
            l_data2.append(data2)
            print(f"List 2: {len(l_data2)}")
            uart_client2.data_recv = None
        if len(l_data1) > 8 and len(l_data2) > 8:
            print("Data 1 received:")
            print(l_data1)
            print("Data 2 received:")
            print(l_data2)
            l_data1 = []
            l_data2 = []
            break
        
        frequency = 1/(time.time() - start_time)
        if count >= frequency/2:
            count = 0
            start_time = time.time()
            data = "ms"
            uart_client1.data_send = data
            uart_client2.data_send = data
        count += 1
        
        
    
    print("Connection closed.")
