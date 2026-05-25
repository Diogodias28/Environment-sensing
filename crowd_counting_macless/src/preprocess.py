import os
import numpy as np
from scipy.signal import butter, filtfilt
from numpy.lib.stride_tricks import sliding_window_view

def apply_lowpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data, axis=0)

def normalize_data(data):
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0)
    return (data - mean) / (std + 1e-8)

def create_valid_windows(X, y, window_size, step_size):
    X_windows_raw = sliding_window_view(X, window_shape=window_size, axis=0)[::step_size]
    X_windows = np.swapaxes(X_windows_raw, 1, 2) 
    
    y_windows = sliding_window_view(y, window_shape=window_size)[::step_size]
    
    valid_indices = np.all(y_windows == y_windows[:, 0:1], axis=1)
    
    X_clean = X_windows[valid_indices]
    y_clean = y_windows[valid_indices, 0]
    
    return X_clean, y_clean

def run_preprocessing_pipeline(input_x_path, input_y_path, output_dir, config):
    if not os.path.exists(input_x_path) or not os.path.exists(input_y_path):
        raise FileNotFoundError("Raw parsed arrays not found. Run data_parser.py first.")
        
    X_raw = np.load(input_x_path)
    y_raw = np.load(input_y_path)
    
    X_filtered = apply_lowpass_filter(X_raw, cutoff=config['cutoff_hz'], fs=config['sampling_rate_hz'])
    X_normalized = normalize_data(X_filtered)
    
    X_windows, y_windows = create_valid_windows(
        X_normalized, 
        y_raw, 
        window_size=config['window_size'], 
        step_size=config['step_size']
    )
    
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, "X_train_ready.npy"), X_windows)
    np.save(os.path.join(output_dir, "y_train_ready.npy"), y_windows)
    
    return X_windows.shape, y_windows.shape

if __name__ == "__main__":
    CONFIG = {
        'sampling_rate_hz': 1000,  
        'cutoff_hz': 10,           
        'window_size': 500,        
        'step_size': 250           
    }
    
    input_x = "../data/parsed/X_raw.npy"
    input_y = "../data/parsed/y_raw.npy"
    output_dir = "../data/processed/"
    
    x_shape, y_shape = run_preprocessing_pipeline(input_x, input_y, output_dir, CONFIG)
    print(f"Preprocessing Complete. Final X shape: {x_shape}, Final y shape: {y_shape}")