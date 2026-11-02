"""Selector, mediana y escala entrenados una vez; aplicables a observaciones nuevas."""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, FunctionTransformer
from sklearn.pipeline import Pipeline


class FeatureSelector(TransformerMixin, BaseEstimator):
    def __init__(self, columns):
        self.columns = columns

    def fit(self, X, y=None):
        self.transform(X)
        self.feature_names_in_ = np.asarray(self.columns, dtype=object)
        self.n_features_in_ = len(self.columns)
        return self

    def transform(self, X):
        if not set(self.columns).issubset(X):
            raise ValueError("La observación no contiene las variables seleccionadas.")
        return X.loc[:, self.columns].astype(float)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(self.columns, dtype=object)


def make_preprocessor(features, robust=True):
    return Pipeline([("select", FeatureSelector(list(features))),
                     ("impute", SimpleImputer(strategy="median", add_indicator=False)),
                     ("scale", RobustScaler(quantile_range=(25., 75.)) if robust else FunctionTransformer())])


def preprocessing_metadata(preprocessor):
    features = list(preprocessor.named_steps["select"].columns)
    scaler = preprocessor.named_steps["scale"]
    return {"features": features, "imputation": "training_median; optional values only; no added missing indicators",
            "medians": dict(zip(features, preprocessor.named_steps["impute"].statistics_.tolist())),
            "centers": dict(zip(features, scaler.center_.tolist())) if hasattr(scaler, "center_") else {},
            "scales": dict(zip(features, scaler.scale_.tolist())) if hasattr(scaler, "scale_") else {},
            "robust_scaler": hasattr(scaler, "center_"), "fit_scope": "eligible training rows only"}
