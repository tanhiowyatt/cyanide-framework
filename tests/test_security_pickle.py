import unittest
import pickle
import io
import os
import sys

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from core.security import loads as safe_loads

class TestRestrictedUnpickler(unittest.TestCase):
    def test_safe_builtins(self):
        """Test that safe builtins like dict, list, int are allowed."""
        safe_data = {'a': 1, 'b': [1, 2, 3], 'c': (4, 5)}
        pickled = pickle.dumps(safe_data)
        unpickled = safe_loads(pickled)
        self.assertEqual(safe_data, unpickled)

    def test_unsafe_os_system(self):
        """Test that os.system is blocked."""
        # Create a malicious payload
        class Malicious:
            def __reduce__(self):
                import os
                return (os.system, ('echo hacked',))
        
        pickled = pickle.dumps(Malicious())
        
        with self.assertRaises(pickle.UnpicklingError) as cm:
            safe_loads(pickled)
        
        self.assertIn("Unsafe class", str(cm.exception))

    def test_unsafe_subprocess(self):
        """Test that subprocess.Popen is blocked."""
        class Malicious2:
            def __reduce__(self):
                import subprocess
                return (subprocess.Popen, (['ls'],))
        
        pickled = pickle.dumps(Malicious2())
        with self.assertRaises(pickle.UnpicklingError):
            safe_loads(pickled)

    def test_ml_model_allowlist(self):
        """Test that whitelisted ML modules (numpy, sklearn) are allowed."""
        try:
            import numpy as np
            from sklearn.cluster import MiniBatchKMeans
        except ImportError:
            self.skipTest("ML libraries not installed")

        # Create a real mini ML object
        kmeans = MiniBatchKMeans(n_clusters=2)
        # We need to fit it to have some state usually, but empty might pickl too
        kmeans.fit([[0], [1], [2]])
        
        pickled = pickle.dumps(kmeans)
        
        # This should pass if sklearn/numpy are correctly whitelisted
        unpickled = safe_loads(pickled)
        self.assertIsInstance(unpickled, MiniBatchKMeans)

if __name__ == "__main__":
    unittest.main()
