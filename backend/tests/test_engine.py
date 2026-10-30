import numpy as np
import pandas as pd
import pytest
from gapguard.numerical import (newton_poly,lagrange_poly,newton_forward_backward,divided_differences,ROOT_SOLVERS)
from gapguard.engine import validate_input,recover,masking_benchmark
from gapguard.demo import demo_data

def test_polynomial_exact():
    x=[0,1,2];y=[1,4,9]
    for p in [newton_poly(x,y),lagrange_poly(x,y),newton_forward_backward(x,y),newton_forward_backward(x,y,'backward')]:
        assert abs(p(1.5)-6.25)<1e-9

def test_root_methods():
    for name,solver in ROOT_SOLVERS.items():
        r=solver(lambda x:x*x-2,1,2)
        assert r.converged,(name,r)
        assert abs(r.root-np.sqrt(2))<1e-5

def test_demo_recovery():
    data,truth=demo_data();out,gaps=recover(data,minutes=5,max_gap=5,threshold=8)
    assert len(gaps)==1 and gaps[0]['status']=='Estimated'
    assert out.estimated.notna().sum()==5
    assert any(r['timestamp'] for r in gaps[0]['estimated_crossings'])
    assert set(out.provenance)=={'measured','estimated'}

def test_long_gap_no_fabrication():
    data,_=demo_data();out,gaps=recover(data,minutes=5,max_gap=3)
    assert gaps[0]['status']=='Unknown'
    assert not out.estimated.notna().any()

def test_no_extrapolation():
    data,_=demo_data();data.loc[0,'value']=float('nan')
    out,gaps=recover(data,minutes=5,max_gap=5)
    assert any('Edge gap' in g['reason'] for g in gaps)

def test_bad_data():
    with pytest.raises(ValueError):validate_input(pd.DataFrame({'foo':[1,2]}))

def test_masking():
    data,_=demo_data();score=masking_benchmark(data,minutes=5)
    assert score['n']>0 and score['mae']>=0

from gapguard.engine import compare_interpolators, threshold_sensitivity

def test_all_methods_same_holdouts():
    source,_=demo_data()
    rows=compare_interpolators(source,minutes=5,max_evals=12)
    assert len(rows)==5
    assert len({r['eligible'] for r in rows})==1
    assert all(r['evaluated']<=r['eligible'] for r in rows)
    assert all(r['rmse'] is None or r['rmse']>=0 for r in rows)

def test_whatif_thresholds():
    source,_=demo_data()
    out,gaps=recover(source,minutes=5,max_gap=5,threshold=8)
    result=threshold_sensitivity(out,gaps[0],[7,8,9])
    assert len(result)==3
    assert any(row['crossing_count']>=1 for row in result)
    for row in result:
        if row['first_crossing_index'] is not None:
            assert 0<=row['first_crossing_index']<len(out)
