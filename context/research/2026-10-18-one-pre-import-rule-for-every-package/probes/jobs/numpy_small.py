"""import numpy and a small array job."""
import numpy as np
a = np.arange(10_000, dtype=np.float64).reshape(100, 100)
print(float(a.sum()), float(np.linalg.det(a[:5, :5] + np.eye(5))), a.mean(axis=0)[:3].tolist())
