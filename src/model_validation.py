"""Huellas del estado aprendido, sin depender de alias internos de objetos copiados."""
import hashlib
import json
import numpy as np
from .model_preprocessing import preprocessing_metadata


def learned_pipeline_fingerprint(pipeline):
    """Incluye parámetros, medianas/escalas y todos los campos de cada árbol.

    Se serializan los campos numéricos por separado: padding de arrays
    estructurados y alias de memoria no forman parte del modelo aprendido.
    """
    digest = hashlib.sha256()
    model = pipeline.named_steps["model"]

    def header(value):
        digest.update(json.dumps(value, sort_keys=True, default=lambda x: x.item(), allow_nan=False).encode())

    def array(value):
        a = np.ascontiguousarray(value)
        header({"shape": a.shape, "dtype": a.dtype.str})
        digest.update(a.tobytes())

    header(preprocessing_metadata(pipeline[:-1]))
    header(model.get_params(deep=False))
    header({"offset": float(model.offset_), "max_samples": int(model.max_samples_), "input_features": int(model.n_features_in_)})
    array(model._seeds)
    for estimator, features in zip(model.estimators_, model.estimators_features_):
        header(estimator.get_params(deep=False))
        state = estimator.tree_.__getstate__()
        header({"max_depth": state["max_depth"], "node_count": state["node_count"]})
        for field in state["nodes"].dtype.names:
            header(field); array(state["nodes"][field])
        array(state["values"]); array(features)
    return digest.hexdigest()
