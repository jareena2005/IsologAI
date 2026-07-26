import os
import sys
import django

# Add project root and apps/ directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import numpy as np
from apps.logs.models import LogEntry
from apps.detection.feature_extraction import extract_features_model
from apps.detection.model_manager import ModelManager

def main():
    print("Fetching log entries from database...")
    logs = LogEntry.objects.all()
    count = logs.count()
    print(f"Found {count} log entries in database.")

    if count < 10:
        print("Error: Minimum of 10 log entries is required to fit the Isolation Forest model.")
        sys.exit(1)

    print("Extracting features from logs...")
    X = []
    for log in logs:
        features = extract_features_model(log)
        X.append(features)

    X = np.array(X)
    print(f"Feature matrix loaded with shape: {X.shape}")

    print("Training Isolation Forest model...")
    manager = ModelManager()
    manager.retrain(X, contamination=0.05)
    print(f"Successfully fit and saved new model. Version ID: {manager.version}")

if __name__ == '__main__':
    main()
