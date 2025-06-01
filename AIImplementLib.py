import os
import numpy as np
import pandas as pd
import tensorflow as tf
import threading
import logging
import time
from abc import ABC, abstractmethod
from scipy.signal import savgol_filter
import socket, serial
from multiprocessing import Queue

class ImplementAIModel(ABC):
    @abstractmethod
    def load_model(self, model_filename):
        pass

    @abstractmethod
    def set_min_max_list(self, min_max_list):
        pass

    @abstractmethod
    def set_window_size(self, window_size):
        pass

    @abstractmethod
    def predict_phase(self, X):
        pass
    
    def Scaler_Data(self, X):
        sca = np.ones_like(X)
        for i in range(len(X)):
            for j in range(len(X[i])):
                sca[i][j] = (X[i][j] - self.min_max_list[j][0]) / (self.min_max_list[j][1] - self.min_max_list[j][0])
        return sca

# Define the model class
class CyclingAIModelH5(ImplementAIModel):
    def __init__(self):
        self.model = None
        self.min_max_list = None
        self.window_size = 5
        

    def load_model(self, model_filename):
        if not os.path.exists(model_filename):
            return False
        try:
            self.model = tf.keras.models.load_model(model_filename)
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
        
    def set_min_max_list(self, min_max_list):
        self.min_max_list = min_max_list
    
    def set_window_size(self, window_size):
        self.window_size = window_size

    def predict_phase(self, X):
        input_data = X
        input_data = self.Scaler_Data(input_data)
        input_data = input_data.reshape(1, input_data.shape[0], input_data.shape[1])
        output = np.argmax(self.model.predict(input_data, verbose=0), axis=1)
        return output[0] + 1
    
class CyclingAIModeltflite(ImplementAIModel):
    def __init__(self):
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.min_max_list = None
        self.window_size = 5
    
    def load_model(self, model_filename):
        if not os.path.exists(model_filename):
            return False
        try:
            self.interpreter = tf.lite.Interpreter(model_path=model_filename)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    def set_min_max_list(self, min_max_list):
        self.min_max_list = min_max_list
    
    def set_window_size(self, window_size):
        self.window_size = window_size
    
    def predict_phase(self, X):
        input_data = X
        input_data = self.Scaler_Data(input_data)
        input_data = input_data.reshape(1, input_data.shape[0], input_data.shape[1])
        input_data = input_data.astype(np.float32)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        output = self.interpreter.get_tensor(self.output_details[0]['index'])
        return np.argmax(output, axis=1)[0] + 1

class CyclingProcessingData:
    def __init__(self, data, data_name):
        self.data = data
        self.list_data = [data for data in range(6)]
        self.data_name = data_name
        self.derivative = None
        
    def update_data(self, data):
        self.data = data
        self.list_data = self.list_data[1:].copy()
        self.list_data.append(self.data)
        
    def derivative_data(self):
        # Apply Savitzky-Golay filter for derivative calculation
        if self.data_name == 'vel':
            self.derivative = savgol_filter(self.list_data, window_length=3, polyorder=2, deriv=1)
        elif self.data_name in ('Tau_1', 'Tau_2'):
            self.derivative = savgol_filter(self.list_data, window_length=5, polyorder=3, deriv=1)
        elif self.data_name == 'Tau_Motor':
            self.derivative = savgol_filter(self.list_data, window_length=5, polyorder=2, deriv=1)
        return self.derivative[-1]
    
class CyclingQueue:
    def __init__(self, max_queue):
        self.max_queue = max_queue
        self.data_queue = Queue(maxsize=self.max_queue)
    def send_data(self):
        self.data_queue.put()
        
class ThreadManager:
    def __init__(self):
        self.threads = {}
        self.running = True
        self.logger = logging.getLogger(__name__)

    def start_thread(self, name, target, fps=30, args=(), kwargs={}):
        """Starts a new thread with a specific FPS and arguments."""
        if name in self.threads:
            self.logger.warning(f"Thread '{name}' is already running.")
            return
        
        frame_time = 1.0 / fps
        stop_event = threading.Event()  # Per-thread stop event
        self.threads[name] = stop_event

        def wrapper():
            while not stop_event.is_set():
                start_time = time.perf_counter()
                target(*args, **kwargs)  # Execute function

                # Ensure frame rate control
                elapsed_time = time.perf_counter() - start_time
                wait_time = max(0, frame_time - elapsed_time)
                stop_event.wait(wait_time)

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def stop_thread(self, name):
        """Stops a specific thread."""
        if name in self.threads:
            self.threads[name].set()  # Signal the thread to stop
            del self.threads[name]
            self.logger.info(f"Thread '{name}' stopped.")

    def stop_all(self):
        """Stops all running threads."""
        for name, stop_event in list(self.threads.items()):
            stop_event.set()
        self.threads.clear()
        self.logger.info("All threads stopped.")
    

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
                # logging.info(f"Received: {msg}")
                # if not self.data_recv.full:
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
        
class UartClient:
    def __init__(self, sever_host="/dev/ttyUSB0", server_port=9600, max_queue=20):
        self.server_host = sever_host
        self.server_port = server_port
        self.serial_obj = serial.Serial(self.server_host, self.server_port, timeout=1)
        self.data_send = None
        self.data_recv = Queue(maxsize=max_queue)
        self.is_running = True
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
        while self.is_running:
            if self.serial_obj.in_waiting > 0:
                data = self.serial_obj.readline().decode("utf-8").strip()
            if not data:
                continue
            else:
                logging.info(f"{self.server_host} received: {data}")
                # if not self.data_recv.full:
                self.data_recv.put(data)
                data = None
            # self.serial_obj.write(response.encode())
        
    def client_handler(self):
        while self.is_running:
            if self.data_send is not None:
                data = self.data_send
                self.data_send = None
                # print(f"Sending: {data}")
                self.serial_obj.write(data.encode())
            time.sleep(0.05)
    
    def start_threads(self):
        threading.Thread(target=self.server_handler, daemon=True).start()
        threading.Thread(target=self.client_handler, daemon=True).start()
        
