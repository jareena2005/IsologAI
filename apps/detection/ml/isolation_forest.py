import os
import joblib
from sklearn.ensemble import IsolationForest

class IsolationForestModel:
    """
    Wrapper for scikit-learn's Isolation Forest model to handle train, predict, save, and load operations.
    """
    def __init__(self, contamination=0.05, random_state=42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=self.contamination, 
            random_state=self.random_state,
            n_estimators=100
        )
        self.is_fitted = False

    def train(self, X):
        """
        Trains the Isolation Forest model on numerical features X.
        """
        if len(X) == 0:
            raise ValueError("Cannot train on empty dataset.")
        self.model.fit(X)
        self.is_fitted = True
        return self

    def predict(self, X):
        """
        Predicts if samples in X are anomalies.
        Returns: List of booleans (True if anomaly, False if normal)
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained yet.")
        preds = self.model.predict(X)
        # IsolationForest returns -1 for anomalies and 1 for inliers
        return [p == -1 for p in preds]

    def score_samples(self, X):
        """
        Computes anomaly score of input samples.
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained yet.")
        return self.model.score_samples(X)

    def save(self, filepath):
        """
        Persists the trained model to disk.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'is_fitted': self.is_fitted,
            'contamination': self.contamination,
            'random_state': self.random_state
        }, filepath)

    @classmethod
    def load(cls, filepath):
        """
        Loads a saved model from disk.
        """
        data = joblib.load(filepath)
        obj = cls(contamination=data['contamination'], random_state=data['random_state'])
        obj.model = data['model']
        obj.is_fitted = data['is_fitted']
        return obj
