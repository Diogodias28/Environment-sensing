import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from cnn_model import build_csi_cnn

def load_and_split_data(input_dir, train_ratio=0.70, val_ratio=0.15):
    x_path = os.path.join(input_dir, "X_train_ready.npy")
    y_path = os.path.join(input_dir, "y_train_ready.npy")
    
    if not os.path.exists(x_path) or not os.path.exists(y_path):
        raise FileNotFoundError(f"Processed data not found at {input_dir}. Run preprocess.py first.")
        
    X = np.load(x_path)
    y = np.load(y_path)
    
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    X = X[indices]
    y = y[indices]
    
    train_idx = int(train_ratio * len(X))
    val_idx = int((train_ratio + val_ratio) * len(X))
    
    X_train, y_train = X[:train_idx], y[:train_idx]
    X_val, y_val = X[train_idx:val_idx], y[train_idx:val_idx]
    X_test, y_test = X[val_idx:], y[val_idx:]
    
    np.save(os.path.join(input_dir, "X_test_buffer.npy"), X_test)
    np.save(os.path.join(input_dir, "y_test_buffer.npy"), y_test)
    
    return (X_train, y_train), (X_val, y_val), (X_test, y_test)

def create_dataloader(X, y, batch_size, shuffle=True):
    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.long)
    dataset = TensorDataset(X_tensor, y_tensor)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)

if __name__ == "__main__":
    # ==========================================
    # EXECUTION (Manual Configuration Required)
    # ==========================================
    
    CONFIG = {
        'input_dir': "../data/processed/",
        'model_dir': "../models/",
        'num_classes': 9,
        'batch_size': 32,
        'epochs': 300,
        'learning_rate': 2e-5,
        'weight_decay': 1e-2,
        'patience': 15
    }
    
    os.makedirs(CONFIG['model_dir'], exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    print("Loading and splitting dataset...")
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = load_and_split_data(CONFIG['input_dir'])
    
    print(f"Training shapes -> X: {X_train.shape}, y: {y_train.shape}")
    print(f"Validation shapes -> X: {X_val.shape}, y: {y_val.shape}")
    print(f"Test split saved for simulator -> X: {X_test.shape}")
    
    X_train = np.expand_dims(X_train, axis=1)
    X_val = np.expand_dims(X_val, axis=1)
    X_test = np.expand_dims(X_test, axis=1)
    
    train_loader = create_dataloader(X_train, y_train, CONFIG['batch_size'], shuffle=True)
    val_loader = create_dataloader(X_val, y_val, CONFIG['batch_size'], shuffle=False)
    test_loader = create_dataloader(X_test, y_test, CONFIG['batch_size'], shuffle=False)
    
    input_shape = (X_train.shape[2], X_train.shape[3])
    model = build_csi_cnn(input_shape=input_shape, num_classes=CONFIG['num_classes']).to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=CONFIG['learning_rate'], weight_decay=CONFIG['weight_decay'])
    
    checkpoint_path = os.path.join(CONFIG['model_dir'], "cnn_weights_best.pt")
    
    print("\nStarting model training...")
    best_val_loss = float('inf')
    patience_counter = 0
    
    for epoch in range(CONFIG['epochs']):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            train_total += targets.size(0)
            train_correct += (predicted == targets).sum().item()
            
        train_acc = train_correct / train_total
        train_loss /= len(train_loader)
        
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += targets.size(0)
                val_correct += (predicted == targets).sum().item()
                
        val_acc = val_correct / val_total
        val_loss /= len(val_loader)
        
        print(f"Epoch {epoch+1}/{CONFIG['epochs']} - loss: {train_loss:.4f} - accuracy: {train_acc:.4f} - val_loss: {val_loss:.4f} - val_accuracy: {val_acc:.4f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), checkpoint_path)
            print(f"Epoch {epoch+1}: val_loss improved. Saving model to {checkpoint_path}")
        else:
            patience_counter += 1
            if patience_counter >= CONFIG['patience']:
                print(f"Epoch {epoch+1}: early stopping")
                break
                
    print("\nEvaluating best model on held-out test split...")
    model.load_state_dict(torch.load(checkpoint_path))
    model.eval()
    test_correct = 0
    test_total = 0
    
    with torch.no_grad():
        for inputs, targets in test_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs.data, 1)
            test_total += targets.size(0)
            test_correct += (predicted == targets).sum().item()
            
    test_accuracy = test_correct / test_total
    print(f"Test Set Accuracy: {test_accuracy * 100:.2f}%")