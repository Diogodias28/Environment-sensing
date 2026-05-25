import os
import glob
import numpy as np
import csiread

def extract_amplitude(file_path):
    csidata = csiread.Intel(file_path)
    csidata.read()
    
    scaled_csi = csidata.get_scaled_csi()
    
    return np.abs(scaled_csi).reshape(scaled_csi.shape[0], -1)

def load_and_label_data(base_dir="../data"):
    search_pattern = os.path.join(base_dir, "Room*", "*")
    file_paths = glob.glob(search_pattern)
    
    if not file_paths:
        raise FileNotFoundError(f"Missing data directory or files at {search_pattern}. Verify project structure.")
        
    all_data = []
    all_labels = []
    
    for file_path in file_paths:
        filename = os.path.basename(file_path)
        
        clean_name = filename.replace('.bin', '')
        
        if not clean_name.endswith('p') or not clean_name[:-1].isdigit():
            continue
            
        label = int(clean_name[:-1])
        amplitude_data = extract_amplitude(file_path)
        labels = np.full((amplitude_data.shape[0],), label, dtype=np.int32)
        
        all_data.append(amplitude_data)
        all_labels.append(labels)
        
    X_raw = np.vstack(all_data)
    y_raw = np.concatenate(all_labels)
    
    return X_raw, y_raw

if __name__ == "__main__":
    X, y = load_and_label_data()
    
    os.makedirs("../data/parsed", exist_ok=True)
    np.save("../data/parsed/X_raw.npy", X)
    np.save("../data/parsed/y_raw.npy", y)
