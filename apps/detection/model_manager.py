import os
import threading
from django.conf import settings
from .ml.isolation_forest import IsolationForestModel

class ModelManager:
    """
    Singleton manager class to load, query, and cache the ML Isolation Forest model thread-safely.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ModelManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_filename='isolation_forest_latest.joblib'):
        if self._initialized:
            return
        
        self.model_filename = model_filename
        # Path to storage of joblib files
        self.model_path = os.path.join(
            settings.BASE_DIR, 'apps', 'detection', 'ml', 'saved_models', self.model_filename
        )
        self.model = None
        self.version = 'default_fallback'
        self.lock = threading.Lock()
        self.load_model()
        self._initialized = True

    def load_model(self):
        """
        Loads the model from disk or initializes a fallback if not found.
        """
        with self.lock:
            if os.path.exists(self.model_path):
                try:
                    self.model = IsolationForestModel.load(self.model_path)
                    mtime = os.path.getmtime(self.model_path)
                    self.version = f"v_{int(mtime)}"
                except Exception:
                    self.model = None
            
            if not self.model:
                self.model = IsolationForestModel()
                self.version = 'untrained_fallback'

    def score_log(self, features):
        """
        Scores a single feature list.
        Returns: (score, is_anomaly)
        """
        with self.lock:
            if not self.model.is_fitted:
                # Return standard values if model is not trained yet
                return 0.0, False
            
            score = float(self.model.score_samples([features])[0])
            is_anomaly = bool(self.model.predict([features])[0])
            return score, is_anomaly

    def retrain(self, X_train, contamination=0.05):
        """
        Retrains the model with a new batch of features X_train and saves it.
        """
        with self.lock:
            new_model = IsolationForestModel(contamination=contamination)
            new_model.train(X_train)
            new_model.save(self.model_path)
            
            self.model = new_model
            mtime = os.path.getmtime(self.model_path)
            self.version = f"v_{int(mtime)}"
