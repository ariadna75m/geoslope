import numpy as np
import pandas as pd
import joblib
import pytest
from src.model_preprocessing import make_preprocessor,preprocessing_metadata

def test_training_medians_scaler_and_future_values_do_not_refit():
    training=pd.DataFrame({'a':[1.,2.,np.nan,4.],'b':[-2.,0.,2.,4.],'prism_id':['P']*4})
    pipeline=make_preprocessor(['a','b']).fit(training)
    metadata=preprocessing_metadata(pipeline)
    assert metadata['medians']=={'a':2.,'b':1.}
    assert metadata['centers']=={'a':2.,'b':1.}
    before=joblib.hash(pipeline)
    transformed=pipeline.transform(pd.DataFrame({'a':[np.nan,1e9],'b':[np.nan,-1e9]}))
    assert np.all(transformed[0]==0) and abs(transformed[1,0])>1e8
    assert joblib.hash(pipeline)==before

def test_new_observation_selection_uses_only_named_numeric_features():
    data=pd.DataFrame({'a':[1.,2.,3.],'b':[3.,4.,5.],'source_record_id':['a','b','c']})
    pipeline=make_preprocessor(['a','b']).fit(data)
    result=pipeline.transform(pd.DataFrame({'a':[2.],'b':[4.]}))
    assert result.shape==(1,2) and np.all(result==0)
    with pytest.raises(ValueError,match='seleccionadas'):pipeline.transform(data.drop(columns='a'))
