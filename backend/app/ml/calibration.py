import numpy as np
from sklearn.linear_model import LogisticRegression


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class PlattCalibratedModel:
    """Wraps a fitted classifier. Rescales its log-odds with a sigmoid fitted on a
    validation set that has the real class ratio (SMOTE-trained models overstate risk)."""

    def __init__(self, base_model, X_val, y_val):
        self.base_model = base_model
        margins = logit(base_model.predict_proba(X_val)[:, 1]).reshape(-1, 1)
        scaler = LogisticRegression(C=1e6, max_iter=1000).fit(margins, y_val)
        self.a = float(scaler.coef_[0][0])
        self.b = float(scaler.intercept_[0])
        assert self.a > 0, "Calibration slope must be positive (monotonic)."

    def calibrate_margin(self, margin):
        return 1.0 / (1.0 + np.exp(-(self.a * np.asarray(margin, dtype=float) + self.b)))

    def predict_proba(self, X):
        p = self.calibrate_margin(logit(self.base_model.predict_proba(X)[:, 1]))
        return np.column_stack([1 - p, p])
