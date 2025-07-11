import os
import tensorflow as tf
import numpy as np
import pandas as pd
from tkinter import Tk, Label, Entry, Button, Frame, PanedWindow, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from AIImplementLib import CyclingAIModelH5, CyclingProcessingData, CyclingAIModeltflite, ThreadManager, TCPConnection
import time, logging, csv, pytz
from datetime import datetime
from multiprocessing import Queue

class PredictionApp:
    def __init__(self, master):
        self.master = master
        master.title("Phase Prediction App")
        master.geometry("1360x800")
        
        self.paned_window = PanedWindow(master, orient="vertical")
        self.paned_window.pack(fill="both", expand=True)
        
        self.interactive_frame = Frame(self.paned_window, padx=600)
        self.paned_window.add(self.interactive_frame, height=160)
        
        Label(self.interactive_frame, text="Level").grid(row=1, column=0, padx=10, pady=10, sticky="E")
        self.entry_a = Entry(self.interactive_frame)
        self.entry_a.grid(row=1, column=1, padx=10, pady=5)
        
        Button(self.interactive_frame, text="  Load Model  ", command=self.load_model).grid(row=3, column=0, columnspan=2, pady=10)
        Button(self.interactive_frame, text="Predict Phase ", command=self.start_predict_phase).grid(row=4, column=0, pady=10)
        Button(self.interactive_frame, text=" Stop Predict ", command=self.stop_predict).grid(row=4, column=1, pady=10)
        
        self.plot_frame = Frame(self.paned_window, bg="white")
        self.paned_window.add(self.plot_frame, height=400)
        
        self. fig, self.ax = self.create_plot()
        self.have_model = False
        self.cycling_model = CyclingAIModeltflite()
        self.raw_data = None
        self.load_data()
        self.thread_manager = ThreadManager()
        self.is_predicting = False
        self.y_true = []
        self.y_pred = []
        
        # Specify the timezone for Ho Chi Minh City
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        # Get the current time in Ho Chi Minh City
        now = datetime.now(tz)
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S") 
        self.fields = ['t','Tau_Motor','Tau_1','Tau_2','vel']
        self.filename = f"Cycling_log_.csv"
        with open(self.filename, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fields)
            writer.writeheader()
        
        client_host = "10.70.132.123"
        client_port = 2000
        server_host = "10.70.132.123"
        server_port = 4000
        self.uart_client = TCPConnection(client_host, client_port, server_host, server_port,max_queue=100)
        self.uart_client.connect_to_server()
        time.sleep(1)
        self.uart_client.start_server()
        self.thread_manager.start_thread("Uart_Client",self.uart_client.server_handler,fps=20)
        self.thread_manager.start_thread("Read_Data",self.uart_client.client_handler,fps=20)
        self.data_queue = Queue(maxsize=20)
    
    
    def updateLog(self, time, Tau_Motor, Tau_1, Tau_2, vel):
        list_append = [{'t': time, 'Tau_Motor': Tau_Motor, 'Tau_1': Tau_1, 'Tau_2': Tau_2, 'vel': vel}]
        with open(self.filename, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fields)
            writer.writerows(list_append)
            csvfile.close()
    
    def load_data(self):
        self.raw_data = pd.read_csv('Datatest/cyclingLabel.csv')
        min_max_df = pd.read_csv('min_max_values.csv')
        min_max_list = list(min_max_df.itertuples(index=False, name=None))
        self.cycling_model.set_min_max_list(min_max_list)
        self.cycling_model.set_window_size(5)
    
    def load_model(self):
        model_filename = 'model/rnn_model2024-12-26_15-43-42.tflite'
        if os.path.exists(model_filename):
            self.cycling_model.load_model(model_filename)
            messagebox.showinfo("Success", "Model loaded successfully")
            self.have_model = True
        else:
            messagebox.showerror("Error", "Model file not found")
    
    def start_predict_phase(self):
        if not self.have_model:
            messagebox.showerror("Error", "Model not loaded!")
            return
        try:
            a = int(self.entry_a.get())
        except ValueError:
            messagebox.showerror("Error", "Enter valid numbers for level.")
            return
        if self.uart_client.is_running:
            # logging.info(f"Sending data: R{a},{b}")
            self.uart_client.data_send = f"F{a}E"
            time.sleep(0.5)
            self.uart_client.data_send = f"RE"
            self.is_predicting = True
            # self.uart_client.send_data(self.uart_client.send_socket, self.uart_client.data_send)
            self.thread_manager.start_thread("Predict_Phase", self.predict_phase, fps=100)
    
    def stop_predict(self):
        logging.info("stop predict phase")
        if self.uart_client.is_running:
            # logging.info(f"Sending data: R{a},{b}")
            self.uart_client.data_send = f"XE"
            self.is_predicting = False
            # self.uart_client.send_data(self.uart_client.send_socket, self.uart_client.data_send)
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
            # self.fig, self.ax = self.create_plot()
            self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
            self.plot_canvas.get_tk_widget().pack(fill="both", expand=True)
            self.update_plot(self.ax, self.y_true, self.y_pred)
            self.y_true = []
            self.y_pred = []    
        # self.master.update_idletasks()
            
    def predict_phase(self):
        input_data = None
        pretime = time.time()
        frequency = 0
        pretime1 = time.time()
        frequency1 = 0
        counter = 0
        print_count = 0
        view_data = self.raw_data.drop(columns=["date", "t", "encoder_count", "period", "degree", "turn", "push_leg", "mode", "Tau_Motor_deriv", "Tau_1_deriv", "Tau_2_deriv", "vel_deriv"])
        view_data_len = len(view_data)
        data_buffer = None
        while self.is_predicting:
            # if not self.uart_client.data_recv.empty:
            data_buffer = self.uart_client.data_recv.get()
            elapsed_time = time.time() - pretime1
            pretime1 = time.time()
            frequency1 = 0.1 / elapsed_time + 0.9 * frequency1
            
            self.uart_client.data_send = f"Have received"
            # l_data = data.split(" ")
            
            if data_buffer is not None:
                # Tau_Motor = float(l_data[1])
                # Tau_1 = float(l_data[3])
                # Tau_2 = float(l_data[5])
                # vel = float(l_data[7])
                # phase = int(l_data[9])
                # counter = int(l_data[13])
                data_buffer = None
                Tau_Motor = float(view_data['Tau_Motor'].values[counter])
                Tau_1 = float(view_data['Tau_1'].values[counter])
                Tau_2 = float(view_data['Tau_2'].values[counter])
                vel = float(view_data['vel'].values[counter])
                phase = int(view_data['phase'].values[counter])
                counter = counter + 1 if counter < view_data_len-1 else 0
                self.updateLog(0, Tau_Motor, Tau_1, Tau_2, vel)
                

                if input_data is None:
                    process_Tau_Motor, process_Tau_1, process_Tau_2, process_vel = CyclingProcessingData(Tau_Motor, 'Tau_Motor'), CyclingProcessingData(Tau_1, 'Tau_1'), CyclingProcessingData(Tau_2, 'Tau_2'), CyclingProcessingData(vel, 'vel')
                    input_data = np.array([[Tau_Motor, Tau_1, Tau_2, vel, process_Tau_Motor.derivative_data(), process_Tau_1.derivative_data(), process_Tau_2.derivative_data(), process_vel.derivative_data()]] * 5)
                else:
                    process_Tau_Motor.update_data(Tau_Motor)
                    process_Tau_1.update_data(Tau_1)
                    process_Tau_2.update_data(Tau_2)
                    process_vel.update_data(vel)
            
                    item = [Tau_Motor, Tau_1, Tau_2, vel, process_Tau_Motor.derivative_data(), process_Tau_1.derivative_data(), process_Tau_2.derivative_data(), process_vel.derivative_data()]
                    input_data = np.append(input_data[1:], [item], axis=0)
                elapsed_time = time.time() - pretime
                pretime = time.time()
                frequency = 0.1 / elapsed_time + 0.9 * frequency
                predict = self.cycling_model.predict_phase(input_data)
                self.y_true.append(phase)
                self.y_pred.append(self.cycling_model.predict_phase(input_data))
                if print_count > frequency/2:
                    print(f"counter {counter}")
                    print(f"Frequency = {frequency:.2f} Hz, recieve speed = {self.uart_client.client_speed:.2f} Hz, true phase = {phase}, predict phase = {predict}, queue size = {self.uart_client.data_recv.qsize()}")
                    print_count = 0
                print_count+=1
                if len(self.y_true) > 500:
                    self.y_true = self.y_true[-500:]
                    self.y_pred = self.y_pred[-500:]
            
    
    def create_plot(self):
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_xlabel("Sample Index")
        ax.set_ylabel("Phase")
        ax.set_title("Predicted vs True Phases")
        ax.grid(True)
        return fig, ax
    
    def update_plot(self, ax, y_true, y_pred):
        diff = [y_true[i] - y_pred[i] for i in range(len(y_true))]
        ax.clear()
        ax.plot(range(max(len(y_pred)-200,0),len(y_pred)), y_pred[max(len(y_pred)-200,0):len(y_pred)], label="Predicted", color='blue')
        ax.plot(range(max(len(diff)-200,0),len(diff)), diff[max(len(diff)-200,0):len(diff)], label="Different", color='green')
        ax.scatter(range(max(len(y_true)-200,0),len(y_true)), y_true[max(len(y_true)-200,0):len(y_true)], color='red', label='True', marker='o', s=20)
        ax.legend()
        ax.grid(True)
        self.plot_canvas.draw()

if __name__ == "__main__":
    root = Tk()
    app = PredictionApp(root)
    logging.basicConfig(level=logging.INFO)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.uart_client.data_send = "bye"
        time.sleep(1)
        app.uart_client.server_socket.close()
        app.uart_client.client_socket.close()
        app.thread_manager.stop_all()
        root.destroy()

    

