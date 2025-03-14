import os
import tensorflow as tf
import numpy as np
import pandas as pd
from tkinter import Tk, Label, Entry, Button, Frame, PanedWindow, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from AIImplementLib import CyclingAIModelH5, CyclingProcessingData, CyclingAIModeltflite
import time

class PredictionApp:
    def __init__(self, master):
        self.master = master
        master.title("Phase Prediction App")
        master.geometry("1360x800")
        
        self.paned_window = PanedWindow(master, orient="vertical")
        self.paned_window.pack(fill="both", expand=True)
        
        self.interactive_frame = Frame(self.paned_window, padx=600)
        self.paned_window.add(self.interactive_frame, height=160)
        
        Label(self.interactive_frame, text="From:").grid(row=1, column=0, padx=10, pady=5, sticky="E")
        self.entry_a = Entry(self.interactive_frame)
        self.entry_a.grid(row=1, column=1, padx=10, pady=5)
        
        Label(self.interactive_frame, text="To:").grid(row=2, column=0, padx=10, pady=5, sticky="E")
        self.entry_b = Entry(self.interactive_frame)
        self.entry_b.grid(row=2, column=1, padx=10, pady=5)
        
        Button(self.interactive_frame, text="Load Model", command=self.load_model).grid(row=3, column=0, columnspan=2, pady=10)
        Button(self.interactive_frame, text="Predict Phase", command=self.predict_phase).grid(row=4, column=0, columnspan=2, pady=10)
        
        self.plot_frame = Frame(self.paned_window, bg="white")
        self.paned_window.add(self.plot_frame, height=400)
        
        self.have_model = False
        self.cycling_model = CyclingAIModeltflite()
        self.load_data()

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
    
    def predict_phase(self):
        if not self.have_model:
            messagebox.showerror("Error", "Model not loaded!")
            return
        
        try:
            a, b = int(self.entry_a.get()), int(self.entry_b.get())
        except ValueError:
            messagebox.showerror("Error", "Enter valid numbers for From and To.")
            return
        
        view_data = self.raw_data[(self.raw_data['period'] >= a) & (self.raw_data['period'] <= b)]
        view_data = view_data.drop(columns=["date", "t", "encoder_count", "level", "period", "degree", "turn", "push_leg", "mode", "Tau_Motor_deriv", "Tau_1_deriv", "Tau_2_deriv", "vel_deriv"])
        X, y = view_data.drop(columns=['phase']).values, view_data['phase'].values
        
        if len(X) < 5:
            messagebox.showerror("Error", "Not enough data points for window size.")
            return
        
        y_pred = []
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        fig, ax = self.create_plot()
        self.plot_canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.plot_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        process_Tau_Motor, process_Tau_1, process_Tau_2, process_vel = [CyclingProcessingData(X[0][i], col) for i, col in enumerate(['Tau_Motor', 'Tau_1', 'Tau_2', 'vel'])]
        input_data = np.array([[X[0][0], X[0][1], X[0][2], X[0][3], process_Tau_Motor.derivative_data(), process_Tau_1.derivative_data(), process_Tau_2.derivative_data(), process_vel.derivative_data()]] * 5)
        start_time = time.time()
        for i in range(len(X)):
            for j, process in enumerate([process_Tau_Motor, process_Tau_1, process_Tau_2, process_vel]):
                process.update_data(X[i][j])
            
            item = [X[i][0], X[i][1], X[i][2], X[i][3], process_Tau_Motor.derivative_data(), process_Tau_1.derivative_data(), process_Tau_2.derivative_data(), process_vel.derivative_data()]
            input_data = np.append(input_data[1:], [item], axis=0)
            elapsed_time = time.time() - start_time
            frequency = (i + 1) / elapsed_time
            print(f"Loop {i + 1}: Frequency = {frequency:.2f} Hz")
            y_pred.append(self.cycling_model.predict_phase(input_data))
        self.update_plot(ax, y[:len(y_pred)], y_pred)
        self.master.update_idletasks()
            
    
    def create_plot(self):
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_xlabel("Sample Index")
        ax.set_ylabel("Phase")
        ax.set_title("Predicted vs True Phases")
        ax.grid(True)
        return fig, ax
    
    def update_plot(self, ax, y_true, y_pred):
        ax.clear()
        ax.plot(range(max(len(y_pred)-200,0),len(y_pred)), y_pred[max(len(y_pred)-200,0):len(y_pred)], label="Predicted", color='blue')
        ax.scatter(range(max(len(y_true)-200,0),len(y_true)), y_true[max(len(y_true)-200,0):len(y_true)], color='red', label='True', marker='o', s=20)
        ax.legend()
        ax.grid(True)
        self.plot_canvas.draw()

root = Tk()
app = PredictionApp(root)
root.mainloop()
