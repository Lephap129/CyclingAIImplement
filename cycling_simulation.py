import time
import logging
from tkinter import Tk, Label, Button, Frame, PanedWindow, Scale, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import PhotoImage
from PIL import Image, ImageTk
import time, logging, csv, pytz
from datetime import datetime
from multiprocessing import Queue
import pandas as pd
import os
import numpy as np


from AIImplementLib import CyclingAIModeltflite, ThreadManager, TCPConnection, CyclingProcessingData



class PredictionApp:
    def __init__(self, master):
        self.master = master
        master.title("Phase Prediction App")
        master.geometry("1360x800")
        master.configure(bg="#f7f7f7")

        # region: Main Layout
        self.paned_window = PanedWindow(master, orient="vertical")
        self.paned_window.pack(fill="both", expand=True)
        # endregion

        # region: Header
        self.introductory_frame = Frame(self.paned_window, padx=2, pady=2, bg="#ffffff")
        self.paned_window.add(self.introductory_frame, height=100)

        self.paned_intro = PanedWindow(self.introductory_frame, orient="horizontal", bg="#ffffff")
        self.paned_intro.pack(fill="both", expand=True)

        # Title
        self.title_frame = Frame(self.paned_intro, padx=10, pady=10, bg="#ffffff")
        self.paned_intro.add(self.title_frame, width=1200)
        Label(
            self.title_frame,
            text="Cycling Phase Simulation Application",
            font=("Helvetica", 22, "bold"),
            fg="#333333",
            bg="#ffffff"
        ).pack(padx=1, pady=1, anchor="center")

        # Logo
        self.logo_frame = Frame(self.paned_intro, padx=10, pady=10, bg="#ffffff")
        self.paned_intro.add(self.logo_frame, width=200)
        image = Image.open("Logo-HCMUTE-Corel.jpg")  # Replace with the actual path to your image
        print( image.size )
        print( (int(image.size[0]/80),int(image.size[1]/80)) )
        image = image.resize((int(image.size[0]/80),int(image.size[1]/80)), Image.ANTIALIAS)  # Resize the image as needed
        self.logo_image = ImageTk.PhotoImage(image)
        Label(self.logo_frame, image=self.logo_image, bg="#ffffff").pack(anchor="e")
        # endregion

        # region: Control Panel
        self.interactive_frame = Frame(self.paned_window, padx=15, pady=15, bg="#f0f0f0", relief="groove", bd=2)
        self.paned_window.add(self.interactive_frame, height=240)
        self.paned_interactive = PanedWindow(self.interactive_frame, orient="horizontal")
        self.paned_interactive.pack(fill="both", expand=True)

        # Controls
        self.control_frame = Frame(self.paned_interactive, padx=10, pady=10, bg="#f0f0f0")
        self.paned_interactive.add(self.control_frame, width=585)

        Label(self.control_frame, text="Configuration Panel", bg="#f0f0f0", font=("Helvetica", 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 15), sticky="w"
        )

        Label(self.control_frame, text="Set Level:", bg="#f0f0f0", font=("Helvetica", 11)).grid(
            row=1, column=0, padx=(10, 5), pady=10, sticky="e"
        )

        self.scale_level = Scale(
            self.control_frame,
            from_=0,
            to=5,
            orient="horizontal",
            length=200,
            troughcolor="#d0d0d0",
            sliderlength=20,
            bg="#f0f0f0"
        )
        self.scale_level.grid(row=1, column=1, padx=10, pady=10)

        Button(
            self.control_frame,
            text="▶ Start",
            font=("Helvetica", 10, "bold"),
            bg="#4caf50",
            fg="white",
            width=18,
            command=self.start_predict_phase,
        ).grid(row=2, column=0, columnspan=2, pady=(10, 5))

        Button(
            self.control_frame,
            text="■ Stop",
            font=("Helvetica", 10, "bold"),
            bg="#f44336",
            fg="white",
            width=18,
            command=self.stop_predict,
        ).grid(row=3, column=0, columnspan=2, pady=5)

        # Tau motor Plot
        self.tau_motor_frame = Frame(self.paned_interactive, padx=5, pady=5, bg="#f0f0f0")
        self.paned_interactive.add(self.tau_motor_frame)

        Label(self.tau_motor_frame, text="Tau Motor Plot", bg="#f0f0f0", font=("Helvetica", 14, "bold")).pack(
            pady=(0, 10), anchor="nw"
        )
        self.plot_tau_motor_frame = Frame(self.tau_motor_frame, bg="#f0f0f0")
        self.plot_tau_motor_frame.pack(fill="both", expand=True)
        self.tau_motor_title = "Tau Motor Data"
        self.tau_motor_xlabel = "Sample Index"
        self.tau_motor_ylabel = "Tau Motor Value"
        self.tau_motor_fig, self.tau_motor_ax = self.create_plot(self.tau_motor_title, self.tau_motor_xlabel, self.tau_motor_ylabel, figsize=(0.5, 0.5), margins={"left": 0.1, "right": 0.95, "top": 0.85, "bottom": 0.25})
        self.tau_motor_plot_canvas = FigureCanvasTkAgg(self.tau_motor_fig, master=self.plot_tau_motor_frame)
        self.tau_motor_plot_canvas.get_tk_widget().pack(fill="both", expand=True)
        # endregion

        # region: Result Plots
        self.result_frame = Frame(self.paned_window, padx=2, pady=2, bg="#f7f7f7")
        self.paned_window.add(self.result_frame, height=400)

        self.paned_result = PanedWindow(self.result_frame, orient="horizontal")
        self.paned_result.pack(fill="both", expand=True)

        # Phase Plot
        self.phase_plot_frame = Frame(self.paned_result, padx=10, pady=10, bg="#f7f7f7")
        self.paned_result.add(self.phase_plot_frame, width=600)
        Label(self.phase_plot_frame, text="Phase Plot", bg="#f7f7f7", font=("Helvetica", 14, "bold")).pack(
            pady=(0, 10), anchor="nw"
        )
        self.plot_phase_frame = Frame(self.phase_plot_frame, bg="#f7f7f7")
        self.plot_phase_frame.pack(fill="both", expand=True)
        self.phase_title = "Phase Data"
        self.phase_xlabel = "Sample Index"
        self.phase_ylabel = "Phase Value"
        self.phase_fig, self.phase_ax = self.create_plot(self.phase_title, self.phase_xlabel,self.phase_ylabel, margins={"left": 0.1, "right": 0.95, "top": 0.92, "bottom": 0.1})
        self.phase_plot_canvas = FigureCanvasTkAgg(self.phase_fig, master=self.plot_phase_frame)
        self.phase_plot_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Force & Velocity Plot
        self.force_velocity_frame = Frame(self.paned_result, padx=10, pady=10, bg="#f7f7f7")
        self.paned_result.add(self.force_velocity_frame, width=600)

        Label(self.force_velocity_frame, text="Force Plot", bg="#f7f7f7", font=("Helvetica", 14, "bold")).pack(
            pady=(0, 10), anchor="nw"
        )
        self.plot_force_frame = Frame(self.force_velocity_frame, bg="#f7f7f7")
        self.plot_force_frame.pack(fill="both", expand=True)
        self.force_title = "Force Data"
        self.force_xlabel = "Sample Index"
        self.force_ylabel = "Force"
        self.force_fig, self.force_ax = self.create_plot(self.force_title, self.force_xlabel, self.force_ylabel, margins={"left": 0.1, "right": 0.95, "top": 0.85, "bottom": 0.25})
        self.force_plot_canvas = FigureCanvasTkAgg(self.force_fig, master=self.plot_force_frame)
        self.force_plot_canvas.get_tk_widget().pack(fill="both", expand=True)

        Label(self.force_velocity_frame, text="Velocity Plot", bg="#f7f7f7", font=("Helvetica", 14, "bold")).pack(
            pady=(0, 10), anchor="nw"
        )
        self.plot_velocity_frame = Frame(self.force_velocity_frame, bg="#f7f7f7")
        self.plot_velocity_frame.pack(fill="both", expand=True)
        self.velocity_title = "Velocity Data"
        self.velocity_xlabel = "Sample Index"
        self.velocity_ylabel = "Velocity"
        self.velocity_fig, self.velocity_ax = self.create_plot(self.velocity_title, self.velocity_xlabel, self.velocity_ylabel, margins={"left": 0.1, "right": 0.95, "top": 0.85, "bottom": 0.25})
        self.velocity_plot_canvas = FigureCanvasTkAgg(self.velocity_fig, master=self.plot_velocity_frame)
        self.velocity_plot_canvas.get_tk_widget().pack(fill="both", expand=True)
        # endregion
        
        # Region: Initialization and Variables
        self.cycling_model = CyclingAIModeltflite()
        self.raw_data = None
        self.load_data()
        self.load_model()
        self.thread_manager = ThreadManager()
        self.is_predicting = False
        self.y_true = []
        self.y_pred = []
        self.y_tau_motor = []
        self.y_force1 = []
        self.y_force2 = []
        self.y_velocity = []
        
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
            
        time.sleep(1)
        self.data_queue = Queue(maxsize=20)
        # endregion
    
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

    def create_plot(self, title, xlabel, ylabel, figsize=(0.5, 0.5), dpi=80, grid=True, legend=True, margins=None):
        """
        Create a matplotlib plot with custom spacing.

        Args:
            title (str): Title of the plot.
            xlabel (str): Label for the x-axis.
            ylabel (str): Label for the y-axis.
            figsize (tuple): Size of the figure.
            dpi (int): Dots per inch for the figure.
            grid (bool): Whether to show grid lines.
            legend (bool): Whether to show the legend.
            margins (dict): Custom margins around the plot (keys: 'left', 'right', 'top', 'bottom').

        Returns:
            tuple: The figure and axis objects.
        """
        fig = Figure(figsize=figsize, dpi=dpi)
        ax = fig.add_subplot(111)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(grid)

        if legend:
            ax.legend()

        # Adjust margins if specified
        if margins:
            fig.subplots_adjust(
                left=margins.get('left', 0.1),
                right=margins.get('right', 0.9),
                top=margins.get('top', 0.9),
                bottom=margins.get('bottom', 0.1)
            )

        return fig, ax
    
    def update_phase_plot(self, ax, plot_canvas, y_true, y_pred, legend=True, grid=True, max_points=200):
        """_summary_

        Args:
            ax (_type_): _description_
            y_true (_type_): _description_
            y_pred (_type_): _description_
            legend (bool, optional): _description_. Defaults to True.
            grid (bool, optional): _description_. Defaults to True.
            max_points (int, optional): _description_. Defaults to 200.
        """
        diff = [y_true[i] - y_pred[i] for i in range(len(y_true))]
        ax.clear()
        ax.set_title(self.phase_title)
        ax.set_xlabel(self.phase_xlabel)
        ax.set_ylabel(self.phase_ylabel)
        ax.plot(range(max(len(y_pred)-max_points,0),len(y_pred)), y_pred[max(len(y_pred)-max_points,0):len(y_pred)], label="Predicted", color='blue')
        ax.plot(range(max(len(diff)-max_points,0),len(diff)), diff[max(len(diff)-max_points,0):len(diff)], label="Different", color='green')
        ax.scatter(range(max(len(y_true)-max_points,0),len(y_true)), y_true[max(len(y_true)-max_points,0):len(y_true)], color='red', label='True', marker='o', s=20)
        if legend: ax.legend()
        ax.grid(grid)
        plot_canvas.draw()
    
    def update_tau_motor_plot(self, y_tau_motor, legend=True, grid=True, max_points=200):
        """_summary_

        Args:
            y_tau_motor (_type_): _description_
            legend (bool, optional): _description_. Defaults to True.
            grid (bool, optional): _description_. Defaults to True.
            max_points (int, optional): _description_. Defaults to 200.
        """
        self.tau_motor_ax.clear()
        self.tau_motor_ax.set_title(self.tau_motor_title)
        self.tau_motor_ax.set_xlabel(self.tau_motor_xlabel)
        self.tau_motor_ax.set_ylabel(self.tau_motor_ylabel)
        self.tau_motor_ax.plot(range(max(len(y_tau_motor)-max_points,0),len(y_tau_motor)), y_tau_motor[max(len(y_tau_motor)-max_points,0):len(y_tau_motor)], label="tau_motor", color='blue')
        if legend: self.tau_motor_ax.legend()
        self.tau_motor_ax.grid(grid)
        self.tau_motor_plot_canvas.draw()
    
    def update_force_plot(self, y_force1, y_force2, legend=True, grid=True, max_points=200):
        """_summary_

        Args:
            y_force1 (_type_): _description_
            y_force2 (_type_): _description_
            legend (bool, optional): _description_. Defaults to True.
            grid (bool, optional): _description_. Defaults to True.
            max_points (int, optional): _description_. Defaults to 200.
        """
        self.force_ax.clear()
        self.force_ax.set_title(self.force_title)
        self.force_ax.set_xlabel(self.force_xlabel)
        self.force_ax.set_ylabel(self.force_ylabel)
        self.force_ax.plot(range(max(len(y_force1)-max_points,0),len(y_force1)), y_force1[max(len(y_force1)-max_points,0):len(y_force1)], label="Force 1", color='blue')
        self.force_ax.plot(range(max(len(y_force2)-max_points,0),len(y_force2)), y_force2[max(len(y_force2)-max_points,0):len(y_force2)], label="Force 2", color='red')
        if legend: self.force_ax.legend()
        self.force_ax.grid(grid)
        self.force_plot_canvas.draw()
        
    def update_velocity_plot(self, y_velocity, legend=True, grid=True, max_points=200):
        """_summary_

        Args:
            y_velocity (_type_): _description_
            legend (bool, optional): _description_. Defaults to True.
            grid (bool, optional): _description_. Defaults to True.
            max_points (int, optional): _description_. Defaults to 200.
        """
        self.velocity_ax.clear()
        self.velocity_ax.set_title(self.velocity_title)
        self.velocity_ax.set_xlabel(self.velocity_xlabel)
        self.velocity_ax.set_ylabel(self.velocity_ylabel)
        self.velocity_ax.plot(range(max(len(y_velocity)-max_points,0),len(y_velocity)), y_velocity[max(len(y_velocity)-max_points,0):len(y_velocity)], label="Velocity", color='blue')
        if legend: self.velocity_ax.legend()
        self.velocity_ax.grid(grid)
        self.velocity_plot_canvas.draw()
    
    def start_predict_phase(self):
        print("Start prediction")
        self.is_predicting = True
        self.thread_manager.start_thread("Predict_Phase", self.predict_phase, fps=100)

    def stop_predict(self):
        print("Stop prediction")
        self.is_predicting = False
        self.thread_manager.stop_thread("Predict_Phase")
        self.update_phase_plot(self.phase_ax,self.phase_plot_canvas, self.y_true, self.y_pred, legend=True, grid=True, max_points=200) 
        self.update_tau_motor_plot(self.y_tau_motor, legend=True, grid=True, max_points=200)
        self.update_force_plot(self.y_force1, self.y_force2, legend=True, grid=True, max_points=200)
        self.update_velocity_plot(self.y_velocity, legend=True, grid=True, max_points=200)
        # Clear data lists
        self.y_true = []
        self.y_pred = []
        self.y_tau_motor = []
        self.y_force1 = []
        self.y_force2 = []
        self.y_velocity = []
        
    def predict_phase(self):
        input_data = None
        pretime = time.time()
        frequency = 0
        pretime1 = time.time()
        frequency1 = 0
        counter = 0
        print_count = 0
        view_data = self.raw_data.drop(columns=["date", "t", "period", "degree", "turn", "push_leg", "mode", "Tau_Motor_deriv", "Tau_1_deriv", "Tau_2_deriv", "vel_deriv"])
        view_data_len = len(view_data)
        while self.is_predicting:
            elapsed_time = time.time() - pretime1
            pretime1 = time.time()
            frequency1 = 0.1 / elapsed_time + 0.9 * frequency1
            
            Tau_Motor = float(view_data['Tau_Motor'].values[counter])
            Tau_1 = float(view_data['Tau_1'].values[counter])
            Tau_2 = float(view_data['Tau_2'].values[counter])
            vel = float(view_data['vel'].values[counter])
            phase = int(view_data['phase'].values[counter])
            counter = counter + 1 if counter < view_data_len-1 else 0
            # self.updateLog(0, Tau_Motor, Tau_1, Tau_2, vel)
            

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
            self.y_tau_motor.append(Tau_Motor)
            self.y_force1.append(Tau_1)
            self.y_force2.append(Tau_2)
            self.y_velocity.append(vel)
            if print_count > frequency/2:
                print(f"counter {counter}")
                print(f"Frequency = {frequency:.2f} Hz, true phase = {phase}, predict phase = {predict}")
                print_count = 0
            print_count+=1
            if len(self.y_true) > 500:
                self.y_true = self.y_true[-500:]
                self.y_pred = self.y_pred[-500:]
                self.y_tau_motor = self.y_tau_motor[-500:]
                self.y_force1 = self.y_force1[-500:]
                self.y_force2 = self.y_force2[-500:]
                self.y_velocity = self.y_velocity[-500:]
                
            self.update_phase_plot(self.phase_ax, self.phase_plot_canvas, self.y_true, self.y_pred, legend=False)
            self.update_tau_motor_plot(self.y_tau_motor, legend=False)
            self.update_force_plot(self.y_force1, self.y_force2, legend=False)
            self.update_velocity_plot(self.y_velocity, legend=False)
            
            


if __name__ == "__main__":
    root = Tk()
    logging.basicConfig(level=logging.INFO)
    app = PredictionApp(root)
    root.mainloop()
