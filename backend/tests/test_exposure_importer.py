import pandas as pd
import pytest
from gapguard.exposure import exposure_analysis
from gapguard.importer import normalize_sensor_data,read_csv_flexible,infer_sampling_minutes

def test_rise_fall_duration_and_exposure():
    frame=pd.DataFrame({'timestamp':pd.date_range('2026-01-01 10:00',periods=3,freq='10min'),
        'value':[5.,10.,5.],'estimated':[float('nan')]*3,'provenance':['measured']*3})
    e=exposure_analysis(frame,upper=8)
    assert len(e)==1
    assert e[0]['duration_min']==pytest.approx(8)
    assert e[0]['degree_minutes']==pytest.approx(8)
    assert e[0]['start']=='2026-01-01 10:06:00'
    assert e[0]['end']=='2026-01-01 10:14:00'

def test_no_bridge_unknown():
    frame=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=3,freq='10min'),
    'value':[10.,float('nan'),10.],'estimated':[float('nan')]*3,'provenance':['measured','unknown','measured']})
    assert exposure_analysis(frame,8)==[]

def test_lower_limit():
    frame=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=3,freq='10min'),
    'value':[4.,0.,4.],'estimated':[float('nan')]*3,'provenance':['measured']*3})
    episodes=exposure_analysis(frame,upper=8,lower=2)
    assert len(episodes)==1 and episodes[0]['kind']=='Low'
    assert episodes[0]['duration_min']==pytest.approx(10)

def test_import_mapping_and_sensor():
    raw=read_csv_flexible(b'date;device;temp\n2026-01-01 10:00;A;4\n2026-01-01 10:05;A;5\n2026-01-01 10:00;B;10\n',separator=';')
    standard,steps=normalize_sensor_data(raw,timestamp_column='date',value_column='temp',sensor_column='device',sensor_id='A')
    assert len(standard)==2 and list(standard.columns)==['timestamp','value']
    assert infer_sampling_minutes(standard)==5

def test_duplicates_rejected():
    raw=pd.DataFrame({'t':['2026-01-01','2026-01-01'],'v':[3,4]})
    with pytest.raises(ValueError,match='Duplicate'):
        normalize_sensor_data(raw,timestamp_column='t',value_column='v')
