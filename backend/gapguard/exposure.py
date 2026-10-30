"""Estimated threshold exposure calculated from a reconstructed, piecewise-linear signal.

This is deliberately separate from real observations. Each segment uses the
Bisection solver from the MATH 301 numerical core for threshold roots.
"""
import numpy as np
import pandas as pd
from .numerical import ROOT_SOLVERS


def exposure_analysis(output, upper, lower=None):
    """Return possible episodes and severity integrals, retaining provenance.

    Do not bridge missing unknown values. A measured-measured linear interval
    is also an *assumption* about what happened between samples.
    """
    if lower is not None and lower>=upper: raise ValueError('Lower limit must be less than upper limit')
    ts=pd.to_datetime(output['timestamp'])
    y=output['value'].combine_first(output['estimated']).to_numpy(dtype=float)
    provenance=output['provenance'].tolist()
    segments=[]
    limits=[('High',float(upper),1)]
    if lower is not None: limits.append(('Low',float(lower),-1))
    for label,limit,sign in limits:
        for i in range(len(y)-1):
            v0,v1=y[i],y[i+1]
            if not np.isfinite(v0) or not np.isfinite(v1): continue
            minutes=(ts.iloc[i+1]-ts.iloc[i]).total_seconds()/60
            if minutes<=0:continue
            # h(u)>0 means outside the configured safe range; u ranges 0..1
            h0,h1=sign*(v0-limit),sign*(v1-limit)
            if h0<=0 and h1<=0:continue
            if h0>0 and h1>0: a,b=0.,1.
            else:
                f=lambda u:float(h0+(h1-h0)*u)
                if h0==0: root=0.
                elif h1==0: root=1.
                else:
                    result=ROOT_SOLVERS['Bisection'](f,0.,1.,tol=1e-12)
                    if not result.converged:continue
                    root=float(result.root)
                a,b=(0.,root) if h0>0 else (root,1.)
            if b-a<=1e-12:continue
            start=ts.iloc[i]+pd.Timedelta(minutes=minutes*a)
            end=ts.iloc[i]+pd.Timedelta(minutes=minutes*b)
            duration=minutes*(b-a)
            # integral of positive degree-excess: trapezoid is exact for a linear segment
            excess0=max(0.,h0+(h1-h0)*a)
            excess1=max(0.,h0+(h1-h0)*b)
            area=duration*(excess0+excess1)/2
            segments.append(dict(kind=label,start=start,end=end,duration_min=duration,
                                 degree_minutes=area,peak_excess=max(excess0,excess1),
                                 estimated=('estimated' in (provenance[i],provenance[i+1])),
                                 sample_start=i,sample_end=i+1))
    episodes=[]
    for kind in ['High','Low']:
        group=sorted([x for x in segments if x['kind']==kind],key=lambda x:x['start'])
        for part in group:
            if episodes and episodes[-1]['kind']==kind and abs((part['start']-episodes[-1]['end']).total_seconds())<0.01:
                e=episodes[-1]
                e['end']=part['end'];e['duration_min']+=part['duration_min']
                e['degree_minutes']+=part['degree_minutes'];e['peak_excess']=max(e['peak_excess'],part['peak_excess'])
                e['estimated']=e['estimated'] or part['estimated'];e['last_index']=part['sample_end']
            else:
                episodes.append({'kind':kind,'start':part['start'],'end':part['end'],
                    'duration_min':part['duration_min'],'degree_minutes':part['degree_minutes'],
                    'peak_excess':part['peak_excess'],'estimated':part['estimated'],
                    'first_index':part['sample_start'],'last_index':part['sample_end']})
    for e in episodes:
        e['start']=e['start'].round('s').isoformat(sep=' ')
        e['end']=e['end'].round('s').isoformat(sep=' ')
        e['status']='Model-estimated' if e['estimated'] else 'Between-readings estimate'
        e['may_be_incomplete']=e['first_index']==0 or e['last_index']==len(y)-1 or (e['first_index']>0 and not np.isfinite(y[e['first_index']-1])) or (e['last_index']<len(y)-1 and not np.isfinite(y[e['last_index']+1]))
        del e['first_index'];del e['last_index']
    episodes.sort(key=lambda e:e['start'])
    return episodes
