import os
import numpy as np
import pandas as pd
import tensorflow as tf
from abc import ABC, abstractmethod
from scipy.signal import savgol_filter

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

# Define the model class
class CyclingAIModelH5(ImplementAIModel):
    def __init__(self):
        self.model = None
        self.min_max_list = None
        self.window_size = 5
        

    def load_model(self, model_filename):
        if os.path.exists(model_filename): 
            self.model = tf.keras.models.load_model(model_filename)
            return True
        else:
            return False
        
    def set_min_max_list(self, min_max_list):
        self.min_max_list = min_max_list
    
    def set_window_size(self, window_size):
        self.window_size = window_size
    
    def Scaler_Data(self, X):
        sca = np.ones_like(X)
        for i in range(len(X)):
            for j in range(len(X[i])):
                sca[i][j] = (X[i][j] - self.min_max_list[j][0]) / (self.min_max_list[j][1] - self.min_max_list[j][0])
        return sca

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
        if os.path.exists(model_filename):
            self.interpreter = tf.lite.Interpreter(model_path=model_filename)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            return True
        else:
            return False
    def set_min_max_list(self, min_max_list):
        self.min_max_list = min_max_list
    
    def set_window_size(self, window_size):
        self.window_size = window_size
    
    def Scaler_Data(self, X):
        sca = np.ones_like(X)
        for i in range(len(X)):
            for j in range(len(X[i])):
                sca[i][j] = (X[i][j] - self.min_max_list[j][0]) / (self.min_max_list[j][1] - self.min_max_list[j][0])
        return sca
    
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