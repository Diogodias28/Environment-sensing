import os
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report

from cnn_model import build_csi_cnn

def generate_confusion_matrix(test_x_path, test_y_path, model_path, config):
    if not os.path.exists(test_x_path) or not os.path.exists(model_path):
        raise FileNotFoundError("Missing test data or model weights. Run train.py first.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluating on device: {device}")

    X_test_raw = np.load(test_x_path)
    y_true = np.load(test_y_path)
    
    X_test = np.expand_dims(X_test_raw, axis=1)
    X_tensor = torch.tensor(X_test, dtype=torch.float32).to(device)

    model = build_csi_cnn(
        input_shape=(config['window_size'], config['num_features']), 
        num_classes=config['num_classes']
    )
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    print("Running inference on test set...")
    with torch.no_grad():
        logits = model(X_tensor)
        _, y_pred_tensor = torch.max(logits, 1)
        
    y_pred = y_pred_tensor.cpu().numpy()

    print("\n" + "="*50)
    print(" CLASSIFICATION REPORT")
    print("="*50)
    print(classification_report(y_true, y_pred, zero_division=0))

    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=range(config['num_classes']), 
                yticklabels=range(config['num_classes']))
    
    plt.title('CSI Crowd Counting - Test Set Confusion Matrix')
    plt.ylabel('True Number of People')
    plt.xlabel('Predicted Number of People')
    
    output_img_path = os.path.join(os.path.dirname(model_path), "confusion_matrix.png")
    plt.tight_layout()
    plt.savefig(output_img_path, dpi=300)
    print(f"\nConfusion matrix plot successfully saved to: {output_img_path}")

if __name__ == "__main__":
    
    CONFIG = {
        'window_size': 500,
        'num_features': 180,
        'num_classes': 9
    }
    
    TEST_X_FILE = "../data/processed/X_test_buffer.npy"
    TEST_Y_FILE = "../data/processed/y_test_buffer.npy"
    SAVED_MODEL_FILE = "../models/cnn_weights_best.pt"
    
    generate_confusion_matrix(TEST_X_FILE, TEST_Y_FILE, SAVED_MODEL_FILE, CONFIG)