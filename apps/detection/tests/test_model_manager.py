import os
import tempfile
import numpy as np
import pytest
from apps.detection.model_manager import ModelManager

@pytest.fixture
def temp_model_manager():
    temp_dir = tempfile.mkdtemp()
    test_filepath = os.path.join(temp_dir, 'test_model.joblib')
    
    # Instantiate or reset singleton for test run
    manager = ModelManager(model_filename='test_model.joblib')
    manager.model_path = test_filepath
    manager.model = None
    manager.load_model()
    
    yield manager
    
    if os.path.exists(test_filepath):
        os.remove(test_filepath)
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass

def test_model_manager_fallback(temp_model_manager):
    # Untrained fallback behavior assertion
    assert temp_model_manager.version == 'untrained_fallback'
    
    score, is_anomaly = temp_model_manager.score_log([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    assert score == 0.0
    assert is_anomaly is False

def test_model_manager_retrain_and_score(temp_model_manager):
    # Generate 15 samples of 6 features
    X_train = np.random.randn(15, 6)
    
    temp_model_manager.retrain(X_train, contamination=0.1)
    
    assert temp_model_manager.version.startswith('v_')
    assert temp_model_manager.model.is_fitted is True
    
    score, is_anomaly = temp_model_manager.score_log([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert isinstance(score, float)
    assert isinstance(is_anomaly, bool)
