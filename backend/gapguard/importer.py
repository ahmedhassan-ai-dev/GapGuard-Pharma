"""Configurable CSV adapter; preserves measured values and documents transformations."""
import io
import pandas as pd
import re


def read_csv_flexible(content: bytes, separator='auto', encoding='utf-8-sig', decimal='.'):
    if len(content) > 20_000_000:
        raise ValueError('File exceeds 20 MB demo limit')
    sep = None if separator == 'auto' else separator
    try:
        frame = pd.read_csv(io.BytesIO(content), sep=sep, engine='python', encoding=encoding, decimal=decimal)
    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise ValueError(f'Could not parse CSV: {exc}') from exc
    if frame.empty or len(frame.columns) < 2:
        raise ValueError('CSV must have at least two columns and one row')
    return frame


def normalize_sensor_data(frame, timestamp_column=None, value_column=None,
                          date_column=None, time_column=None, sensor_column=None,
                          sensor_id=None, unit=None, timezone=None, duplicates='reject'):
    """Converts wide/long CSV to timestamp,value without fabricating observations.

    Optional sensor selection supports long tables with one timestamp, sensor ID and value.
    Timestamp can come from one column or from concatenated date/time columns.
    """
    data=frame.copy()
    transformations=[]
    if sensor_column:
        if sensor_column not in data: raise ValueError('Unknown sensor column')
        if sensor_id is None: raise ValueError('Select one sensor before analysis')
        before=len(data)
        data=data[data[sensor_column].astype(str)==str(sensor_id)].copy()
        transformations.append(f'Filtered sensor {sensor_id}: {before} -> {len(data)} rows')
    if timestamp_column:
        if timestamp_column not in data: raise ValueError('Unknown timestamp column')
        times=data[timestamp_column]
    else:
        if not date_column or not time_column: raise ValueError('Specify a timestamp column or date + time columns')
        times=data[date_column].astype(str).str.strip()+' '+data[time_column].astype(str).str.strip()
        transformations.append('Combined date and time columns')
    if value_column not in data: raise ValueError('Choose a numeric measurement column')
    values=pd.to_numeric(data[value_column],errors='coerce')
    invalid_nonempty=(values.isna() & data[value_column].notna()).sum()
    if invalid_nonempty: raise ValueError(f'{invalid_nonempty} non-numeric values; clean or map the correct column')
    # pandas >=2 strict format inference may reject mixed ISO/US date formats.
    # Try mixed parsing, then standard parsing for older pandas versions.
    try:
        stamps=pd.to_datetime(times,errors='coerce',format='mixed',dayfirst=False,utc=(timezone=='UTC'))
    except (TypeError, ValueError):
        stamps=pd.to_datetime(times,errors='coerce',utc=(timezone=='UTC'))
    if stamps.isna().any(): raise ValueError(f'{stamps.isna().sum()} invalid timestamps')
    if hasattr(stamps.dt,'tz') and stamps.dt.tz is not None:
        stamps=stamps.dt.tz_convert('UTC').dt.tz_localize(None)
        transformations.append('Converted timezone-aware timestamps to naive UTC')
    result=pd.DataFrame({'timestamp':stamps,'value':values})
    if result['timestamp'].duplicated().any():
        if duplicates=='reject': raise ValueError('Duplicate timestamps found. Choose mean/last aggregation only if scientifically justified')
        if duplicates=='mean':
            result=result.groupby('timestamp',as_index=False)['value'].mean()
            transformations.append('Aggregated same-timestamp observations with mean')
        elif duplicates=='last':
            result=result.drop_duplicates('timestamp',keep='last')
            transformations.append('Kept last same-timestamp observation')
        else: raise ValueError('Unknown duplicate policy')
    result=result.sort_values('timestamp').reset_index(drop=True)
    transformations.append(f'Mapped {value_column} -> value' + (f' ({unit})' if unit else ''))
    return result,transformations


def infer_sampling_minutes(data):
    """Suggest a schedule; never assert that irregular data are aligned."""
    t=pd.to_datetime(data['timestamp']).sort_values()
    delta=t.diff().dropna().dt.total_seconds()/60
    positive=delta[delta>0]
    return float(positive.median()) if not positive.empty else None


def suggested_fields(columns):
    """Conservative column suggestions; user must verify mapping."""
    cols=list(columns)
    def canon(s):return re.sub(r'[^a-z0-9]','',str(s).lower())
    def choice(needles):
        for c in cols:
            if canon(c) in needles:return c
        for c in cols:
            if any(n in canon(c) for n in needles):return c
        return None
    stamp=choice({'timestamp','datetime','dateandtime','recordedat','measurementtime','datatime'})
    date=choice({'date','recorddate'})
    clock=choice({'time','clocktime'})
    value=choice({'value','temperature','temperaturec','temp','reading','sensorvalue','tempdegc'})
    sensor=choice({'sensorid','deviceid','loggerid','sensor'})
    return {'timestamp':stamp,'date':date,'time':clock,'value':value,'sensor':sensor}
