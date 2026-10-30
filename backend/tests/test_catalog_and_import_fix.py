import pandas as pd
from gapguard.catalog import CATALOG
from gapguard.importer import suggested_fields, normalize_sensor_data

def test_catalog_20_classes_not_sku_verified():
    assert len(CATALOG)==20
    assert all(not (v.verification=='MANUFACTURER_VERIFIED_EGYPT') for v in CATALOG.values())

def test_combined_datetime_column_detected():
    fields=suggested_fields(['Date & Time','Temperature (°C)','Sensor ID'])
    assert fields['timestamp']=='Date & Time'
    assert fields['value']=='Temperature (°C)'

def test_combined_datetime_csv_from_screenshot():
    frame=pd.DataFrame({'Date & Time':['2026-10-30 09:30:00','2026-10-30 09:35:00'],'Temperature (°C)':[6.2,7.6]})
    parsed,_=normalize_sensor_data(frame,timestamp_column='Date & Time',value_column='Temperature (°C)')
    assert parsed['value'].tolist()==[6.2,7.6]
