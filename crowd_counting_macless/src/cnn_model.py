import torch
import torch.nn as nn

class CSICNN(nn.Module):
    def __init__(self, input_shape, num_classes):
        super(CSICNN, self).__init__()
        
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.3),
            
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.3)
        )
        
        dummy_x = torch.zeros(1, 1, input_shape[0], input_shape[1])
        flattened_size = self.features(dummy_x).view(-1).shape[0]
        
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flattened_size, 64),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def build_csi_cnn(input_shape, num_classes):
    model = CSICNN(input_shape, num_classes)
    return model

if __name__ == "__main__":
    
    CONFIG = {
        'window_size': 500,
        'num_features': 180,  
        'num_classes': 9     
    }
    
    target_input_shape = (CONFIG['window_size'], CONFIG['num_features'])
    
    cnn = build_csi_cnn(
        input_shape=target_input_shape, 
        num_classes=CONFIG['num_classes']
    )
    
    print(cnn)