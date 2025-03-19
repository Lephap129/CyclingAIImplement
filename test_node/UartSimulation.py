import socket

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

class UARTServer:
    def __init__(self, host='127.0.0.1', recv_port=2000, send_port=4000):
        self.host = host
        self.recv_port = recv_port
        self.send_port = send_port
        self.isConnect = False
        self.data_recv = None
        self.data_send = None
    
    def read_data(self, conn):
        """Reads data from the client connection."""
        return conn.recv(1024).decode('utf-8').strip()
    
    def send_data(self, conn, message):
        """Sends data to the client connection."""
        conn.sendall(message.encode('utf-8'))
    
    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as recv_socket:
            recv_socket.bind((self.host, self.recv_port))
            recv_socket.listen()
            print(f"Listening for commands on {self.host}:{self.recv_port}")
            
            conn, addr = recv_socket.accept()
            with conn:
                print(f"Connected by {addr}")
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as send_socket:
                    send_socket.bind((self.host, self.send_port))
                    send_socket.listen()
                    print(f"Listening for response connections on {self.host}:{self.send_port}")
                    
                    send_conn, send_addr = send_socket.accept()
                    with send_conn:
                        print(f"Response connection established with {send_addr}")
                        self.isConnect = True
                        while True:
                            data = self.read_data(conn)
                            if not data:
                                self.data_recv = None
                            elif data.lower() == "exit":
                                break
                            else:
                                self.data_recv = data
                            if self.data_send is not None:
                                self.send_data(send_conn, self.data_send)
                                self.data_send = None

if __name__ == "__main__":
    server = UARTServer()
    server.start_server()
