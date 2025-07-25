import socket
import pandas as pd
import threading
import time, logging
from multiprocessing import Queue
class UartSimulation:
    def __init__(self):
        self.setTorque = 0
        self.setSpd = 0
        self.spd = 0
        self.mode = "None"
        self.RunStatus = 0
        self.pulse = 0
        self.P = 0
        self.lastP = 0
    def process_uart_command(self, data):
        response = ""
        if not data:
            response = "Invalid command"
            return response
        if data == "Have received":
            response = "Sending more data"
            return response
        command = data[0]
        content = data[1:].split('E')[0]  # Extract data before 'E'
        
        if command == 'F':  # Force mode
            self.setTorque = int(content)
            self.mode = "Force"
            response = "Setting force mode"
        
        elif command == 'S':  # Speed mode
            self.spd = int(content)
            self.setSpd = float(content) * 10
            if self.setSpd > 0:
                self.setSpd += 30
            elif self.setSpd < 0:
                self.setSpd -= 30
            self.mode = "Speed"
            response = "Setting speed mode"
        
        elif command == 'X':  # Stop command
            self.RunStatus = 0
            self.setSpd = 0
            self.spd = 0
            self.setTorque = 0
            response = "Stopping"
        
        elif command == 'R':  # Run command
            self.RunStatus = 1
            self.pulse = 0
            self.P = 0
            self.lastP = 0
            response = "Sending more data"
        
        confirm = f"Command: {command}, Mode: {self.mode}, Speed: {self.setSpd}, Torque: {self.setTorque}, RunStatus: {self.RunStatus}"
        print(confirm)
        return response

class TCPConnection:
    def __init__(self, client_host, client_port, server_host, server_port, max_queue=20):
        self.client_host = client_host
        self.client_port = client_port
        self.server_host = server_host
        self.server_port = server_port
        self.client_speed = 0
        self.server_speed = 0
        self.client_socket = None
        self.server_socket = None
        self.client_conn = None
        self.is_running = True
        self.data_send = None
        self.data_recv = Queue(maxsize=max_queue)

    def connect_to_server(self):
        """ Connect to an external server """
        self.client_socket = socket.socket()
        try:
            self.client_socket.connect((self.client_host, self.client_port))
            print(f"Successfully connected to {self.client_host} on port {self.client_port}")
        except Exception as e:
            print(f"Connection failed: {e}")

    def start_server(self):
        """ Start server to listen for incoming connections """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.server_host, self.server_port))
        self.server_socket.listen(1)  # Allow only 1 connection
        print(f"Server listening on {self.server_host}:{self.server_port}")
        
        self.client_conn, addr = self.server_socket.accept()
        print(f"Connected to {addr}")

    def server_handler(self):
        """ Server thread to send messages """
        pretime = time.time()
        while self.is_running:
            if self.data_send is not None:
                message = self.data_send
                elapsed_time = time.time() - pretime
                pretime = time.time()
                self.server_speed = 0.1 / elapsed_time + 0.9 * self.server_speed
                self.data_send = None
                if message.lower() == "bye":
                    self.client_conn.sendall(message.encode())
                    time.sleep(1)
                    self.client_conn.close()
                    self.is_running = False
                    break
                self.client_conn.sendall(message.encode())
                time.sleep(0.05)

    def client_handler(self):
        """ Client thread to receive messages """
        pretime = time.time()
        while self.is_running:
            try:
                msg = self.client_socket.recv(1024).decode()
                if not msg:
                    break
                logging.info(f"Received: {msg}")
                # if not self.data_recv.full():
                self.data_recv.put(msg)
                elapsed_time = time.time() - pretime
                pretime = time.time()
                self.client_speed = 0.1 / elapsed_time + 0.9 * self.client_speed
                if msg.lower() == "bye":
                    self.client_socket.close()
                    self.is_running = False
                    break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
    
    def start_threads(self):
        """ Start both server and client threads """
        threading.Thread(target=self.server_handler, daemon=True).start()
        threading.Thread(target=self.client_handler, daemon=True).start()

if __name__ == "__main__":
    client_host = "10.70.132.123"
    client_port = 4000
    server_host = "10.70.132.123"
    server_port = 2000
    
    tcp_connection = TCPConnection(client_host, client_port, server_host, server_port,max_queue=100)
    uart_data = UartSimulation()
    raw_data = pd.read_csv('Datatest/cyclingLabel.csv')
    view_data = raw_data.drop(columns=["date", "t", "encoder_count", "period", "degree", "turn", "push_leg", "mode", "Tau_Motor_deriv", "Tau_1_deriv", "Tau_2_deriv", "vel_deriv"])
    tcp_connection.start_server()
    time.sleep(1)  # Allow time for server setup
    tcp_connection.connect_to_server()
    tcp_connection.start_threads()
    counter = 0
    count = 0
    pretime = time.time()
    frequency = 0
    response = ""
    run_data = None
    try:
        while tcp_connection.is_running:
            # if tcp_connection.data_recv.empty() == False:
            print("Queue is emty:", tcp_connection.data_recv.empty())
            time.sleep(0.04)
            data = tcp_connection.data_recv.get()
            response = uart_data.process_uart_command(data)
            if response == "Setting force mode":
                if uart_data.setTorque > 0:
                    run_data = view_data.groupby('level').get_group(uart_data.setTorque)
                else:
                    run_data = view_data
                run_length = len(run_data)
            
            if uart_data.RunStatus == 0 and response == "Stopping":
                logging.info("Stopped")
                run_data = None
                counter = 0
                frequency = 0
        
            if uart_data.RunStatus == 1 and response == "Sending more data":
                logging.info("Running")
                if counter == 0:
                    start_time = time.time()
                elif counter == run_length - 1:
                    end_time = time.time()
                    frequency = run_length / (end_time - start_time)
                    print(f"Frequency: {frequency} Hz")
                tcp_connection.data_send = f"M {run_data['Tau_Motor'].values[counter]} TA {run_data['Tau_1'].values[counter]} TB {run_data['Tau_2'].values[counter]} V {run_data['vel'].values[counter]} P {run_data['phase'].values[counter]} f {frequency} C {counter} E"
                counter = counter + 1 if counter < run_length-1 else 0
                # time.sleep(0.01)
                # import pdb; pdb.set_trace()
    except KeyboardInterrupt:
        tcp_connection.data_send = "bye"
        time.sleep(1)
        tcp_connection.is_running = False
        tcp_connection.client_conn.close()
        tcp_connection.server_socket.close()
        tcp_connection.client_socket.close()
    
    print("Connection closed.")
