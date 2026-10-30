import numpy as np
import pandas as pd

def demo_data():
    minutes=np.arange(0,181,5)
    # sampled cold-room warming and recovery; staged synthetic data
    temperature=4+6*np.exp(-((minutes-85)/34)**2)+0.16*np.sin(minutes/8)
    values=temperature.copy()
    values[(minutes>=60)&(minutes<=80)]=np.nan
    return pd.DataFrame({'timestamp':pd.date_range('2026-10-28 10:00',periods=len(minutes),freq='5min'),'value':values}),pd.DataFrame({'timestamp':pd.date_range('2026-10-28 10:00',periods=len(minutes),freq='5min'),'true_value':temperature})
