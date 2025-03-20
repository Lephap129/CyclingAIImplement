import socket
import threading
import time

def process_uart_command(self, data):
    if not data:
        return "Invalid command"
    
    command = data[0]
    content = data[1:].split('E')[0]  # Extract data before 'E'
    
    if command == 'F':  # Force mode
        self.setTorque = float(content) * 1  # Add 1 for stability
        self.mode = "Force"
    
    elif command == 'S':  # Speed mode
        self.spd = int(content)
        self.setSpd = float(content) * 10
        if self.setSpd > 0:
            self.setSpd += 30
        elif self.setSpd < 0:
            self.setSpd -= 30
        self.mode = "Speed"
    
    elif command == 'X':  # Stop command
        self.RunStatus = 0
        self.setSpd = 0
        self.spd = 0
        self.setTorque = 0
    
    elif command == 'R':  # Run command
        self.RunStatus = 1
        self.pulse = 0
        self.P = 0
        self.lastP = 0
    
    response = f"Command: {command}, Mode: {self.mode}, Speed: {self.setSpd}, Torque: {self.setTorque}, RunStatus: {self.RunStatus}"
    print(response)
    return response

class TCPConnection:
    def __init__(self, client_host, client_port, server_host, server_port):
        self.client_host = client_host
        self.client_port = client_port
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        self.server_socket = None
        self.client_conn = None
        self.is_running = True
        self.data_send = None
        self.data_recv = None

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
        while self.is_running:
            if self.data_send is not None:
                message = self.data_send
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
        while self.is_running:
            try:
                msg = self.client_socket.recv(1024).decode()
                if not msg:
                    break
                print(f"Received: {msg}")
                self.data_recv = msg
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
    client_host = "192.168.1.96"
    client_port = 2000
    server_host = "192.168.1.96"
    server_port = 4000
    
    tcp_connection = TCPConnection(client_host, client_port, server_host, server_port)
    tcp_connection.connect_to_server()
    time.sleep(1)  # Allow time for server setup
    tcp_connection.start_server()
    tcp_connection.start_threads()
    
    while tcp_connection.is_running:
        message = input("Send: ")
        tcp_connection.data_send = message
        time.sleep(1)
    
    print("Connection closed.")
