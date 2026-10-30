import io
import pandas as pd
from gapguard.engine import recover
from gapguard.pharma import PROFILES,custom_profile,investigate,assess_batches,generate_pdf

def series(vals):
    return pd.DataFrame({'timestamp':pd.date_range('2026-10-30 10:00',periods=len(vals),freq='5min'),'value':vals})

def test_normal_without_missing_not_certified():
    out,gaps=recover(series([4,5,6,6,5,4]),minutes=5)
    r=investigate(out,PROFILES['vaccine_demo'],gaps)
    assert r['status']=='NO OUT-OF-RANGE READINGS OBSERVED'
    assert r['measured_count']==6 and r['gap_count']==0 and r['episode_count']==0
    assert 'not establish product potency' in r['caveat']

def test_measured_excursion_even_without_gap():
    out,gaps=recover(series([5,7,10,11,7,5]),minutes=5)
    r=investigate(out,PROFILES['vaccine_demo'],gaps)
    assert r['status'].startswith('DOCUMENTED EXCURSION')
    assert r['measured_high_count']==2 and r['episode_count']>=1
    assert r['modeled_exposure_minutes']>0
    assert generate_pdf(r).startswith(b'%PDF')

def test_unknown_gap_no_auto_clearance():
    out,gaps=recover(series([5,None,None,None,None,None,None,5,5]),minutes=5,max_gap=2)
    r=investigate(out,PROFILES['vaccine_demo'],gaps)
    assert r['unknown_count']>0 and r['status'].startswith('INCOMPLETE')

def test_estimated_gap_requires_review_even_with_normal_values():
    out,gaps=recover(series([5,6,None,6,5]),minutes=5,max_gap=2,method='Linear')
    r=investigate(out,PROFILES['vaccine_demo'],gaps)
    assert r['estimated_count']==1 and r['status'].startswith('INCOMPLETE')

def test_batch_overlap():
    out,gaps=recover(series([5,7,10,11,7,5]),minutes=5)
    r=investigate(out,PROFILES['vaccine_demo'],gaps)
    rows=assess_batches(r,[{'batch':'A','in_time':'2026-10-30 10:09','out_time':'2026-10-30 10:16'},
                            {'batch':'B','in_time':'2026-10-30 09:00','out_time':'2026-10-30 09:50'}])
    assert rows[0]['modeled_excursion_overlap_min']>0
    assert rows[1]['modeled_excursion_overlap_min']==0

def test_policy_validation():
    try:custom_profile('Test',9,2,'doc')
    except ValueError:pass
    else:raise AssertionError('Invalid limits accepted')
