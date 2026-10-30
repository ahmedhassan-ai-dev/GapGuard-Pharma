"""Gap investigation: explicit provenance, local models, no claim of certain recovery."""
import numpy as np
import pandas as pd
from .numerical import INTERPOLATORS,ROOT_SOLVERS

REQUIRED=['timestamp','value']

def validate_input(df, minutes=10):
    if not set(REQUIRED).issubset(df.columns): raise ValueError('CSV must have timestamp,value columns')
    if not 1<=minutes<=1440: raise ValueError('Sampling minutes must be 1..1440')
    t=df[['timestamp','value']].copy()
    t['timestamp']=pd.to_datetime(t['timestamp'],errors='coerce')
    if t['timestamp'].isna().any():raise ValueError('Invalid timestamps')
    if t.timestamp.duplicated().any():raise ValueError('Duplicate timestamps; resolve before analysis')
    t['value']=pd.to_numeric(t['value'],errors='coerce')
    t=t.sort_values('timestamp').reset_index(drop=True)
    if len(t)<3:raise ValueError('At least three timestamped rows required')
    if t['value'].dropna().empty:raise ValueError('No measured values')
    interval=pd.Timedelta(minutes=minutes)
    start=t.timestamp.iloc[0]; offsets=(t.timestamp-start)/interval
    if not np.allclose(offsets,np.round(offsets),atol=1e-5):
        raise ValueError('Timestamps do not align to specified sampling interval')
    full=pd.date_range(t.timestamp.min(),t.timestamp.max(),freq=interval)
    if len(full)>100000:raise ValueError('Too many points for interactive analysis')
    out=t.set_index('timestamp').reindex(full).rename_axis('timestamp').reset_index()
    out['provenance']=np.where(out['value'].notna(),'measured','unknown')
    return out

def contiguous_runs(mask):
    idx=np.flatnonzero(mask);runs=[]
    if not len(idx):return runs
    a=b=int(idx[0])
    for item in idx[1:]:
        item=int(item)
        if item!=b+1:runs.append((a,b));a=item
        b=item
    runs.append((a,b))
    return runs

def recover(df,minutes=10,threshold=8.,max_gap=4,method='Newton divided differences',window=2):
    if method not in INTERPOLATORS:raise ValueError('Unknown method')
    if window<1 or window>6:raise ValueError('Context window must be 1..6')
    out=validate_input(df,minutes)
    out['estimated']=np.nan
    investigations=[]
    gaps=contiguous_runs(out['value'].isna().to_numpy())
    for a,b in gaps:
        missing=b-a+1
        record={'from':str(out.timestamp.iloc[a]),'to':str(out.timestamp.iloc[b]),'points':missing,'status':'Unknown','reason':'','estimated_crossings':[],'quality':'Unassessed'}
        if a==0 or b==len(out)-1:
            record['reason']='Edge gap: extrapolation prohibited';investigations.append(record);continue
        if missing>max_gap:
            record['reason']='Gap longer than configured recovery limit';investigations.append(record);continue
        left=list(range(max(0,a-window),a));right=list(range(b+1,min(len(out),b+1+window)))
        context=[i for i in left+right if pd.notna(out.value.iloc[i])]
        if len(context)<2 or not any(i<a for i in context) or not any(i>b for i in context):
            record['reason']='Insufficient measured points bracketing gap';investigations.append(record);continue
        # polynomial degree <= 3: avoid excessive oscillation, maintain nearest two anchors
        if method!='Linear' and len(context)>4:context=context[:2]+context[-2:]
        xs=np.array(context,dtype=float);ys=out.value.iloc[context].to_numpy(dtype=float)
        try:poly=INTERPOLATORS[method](xs,ys)
        except ValueError as exc:record['reason']=str(exc);investigations.append(record);continue
        query=np.arange(a,b+1,dtype=float)
        predicted=np.asarray(poly(query),float)
        if not np.isfinite(predicted).all():record['reason']='Numerical instability';investigations.append(record);continue
        anchor_min,anchor_max=min(ys),max(ys)
        overshoot=np.any((predicted < anchor_min-max(1.,abs(anchor_max-anchor_min))*0.3)|(predicted>anchor_max+max(1.,abs(anchor_max-anchor_min))*0.3))
        if overshoot:
            record['reason']='Implausible polynomial overshoot: manual review';investigations.append(record);continue
        out.loc[a:b,'estimated']=predicted
        out.loc[a:b,'provenance']='estimated'
        record['status']='Estimated';record['quality']='Model-dependent estimate; not a confidence probability'
        # investigate the entire interior interval including bracketing anchors; detect all sign-change crossings
        begin=a-1;end=b+1
        f=lambda z:float(poly(z)-threshold)
        crossings=[]
        sample=np.linspace(begin,end,max(32,16*(end-begin)+1))
        for lo,hi in zip(sample[:-1],sample[1:]):
            flo,fhi=f(lo),f(hi)
            if abs(flo)<1e-9: root=lo
            elif flo*fhi<0:
                result=ROOT_SOLVERS['Bisection'](f,lo,hi)
                if not result.converged:continue
                root=result.root
            else:continue
            if any(abs(root-r)<1e-4 for r in crossings):continue
            crossings.append(root)
        crossings=sorted(crossings)
        record['estimated_crossings']=[{'timestamp':str(out.timestamp.iloc[0]+pd.Timedelta(minutes=c*minutes)),'index':round(float(c),8)} for c in crossings]
        record['crossing_count']=len(crossings)
        investigations.append(record)
    return out,investigations

def root_comparison(out, gap,threshold=8.,method='Newton divided differences'):
    """Compare solvers on the first bracketed sign-change using the same interpolation polynomial."""
    ts=pd.to_datetime(out['timestamp'])
    a=int(np.flatnonzero(ts==pd.Timestamp(gap['from']))[0]);b=int(np.flatnonzero(ts==pd.Timestamp(gap['to']))[0])
    if a<1 or b>=len(out)-1:return []
    ctx=[i for i in range(max(0,a-2),a)]+[i for i in range(b+1,min(len(out),b+3))]
    ctx=[i for i in ctx if pd.notna(out.value.iloc[i])]
    if len(ctx)>4:ctx=ctx[:2]+ctx[-2:]
    if len(ctx)<2:return []
    try:p=INTERPOLATORS[method](np.array(ctx,float),out.value.iloc[ctx].to_numpy(float))
    except ValueError:return []
    f=lambda z:float(p(z)-threshold)
    grid=np.linspace(a-1,b+1,101)
    bracket=next(((float(u),float(v)) for u,v in zip(grid[:-1],grid[1:]) if f(u)*f(v)<0),None)
    if not bracket:return []
    rows=[]
    for name,solver in ROOT_SOLVERS.items():
        import time
        start=time.perf_counter();r=solver(f,*bracket);duration=(time.perf_counter()-start)*1000
        rows.append({'method':name,'root_index':round(r.root,8) if r.root is not None else None,'iterations':r.iterations,'residual':r.residual,'converged':r.converged,'duration_ms':round(duration,5),'note':r.reason})
    return rows

def masking_benchmark(df,minutes=10,method='Newton divided differences',step=3,max_evals=100):
    base=validate_input(df,minutes)
    measured=np.flatnonzero(base.value.notna().to_numpy())
    rows=[]
    for idx in measured:
        if len(rows)>=max_evals:break
        if idx<2 or idx>=len(base)-2 or idx%step!=0:continue
        source=base[['timestamp','value']].copy();actual=float(source.value.iloc[idx]);source.loc[idx,'value']=np.nan
        try:result,_=recover(source,minutes=minutes,max_gap=1,method=method)
        except ValueError:continue
        predicted=result.estimated.iloc[idx]
        if np.isfinite(predicted):rows.append({'timestamp':str(base.timestamp.iloc[idx]),'actual':actual,'estimated':float(predicted),'abs_error':abs(actual-float(predicted))})
    if not rows:return {'n':0,'mae':None,'rmse':None,'rows':[]}
    err=np.array([r['abs_error'] for r in rows])
    return {'n':len(rows),'mae':float(np.mean(err)),'rmse':float(np.sqrt(np.mean(err**2))),'rows':rows}

def compare_interpolators(df, minutes=10, step=3, max_evals=45):
    """Same hold-out positions, with measured coverage and actual reconstruction errors."""
    source=validate_input(df,minutes)
    indices=[int(i) for i in np.flatnonzero(source.value.notna().to_numpy()) if 2<=i<len(source)-2 and i%step==0][:max_evals]
    rows=[]
    for name in INTERPOLATORS:
        errors=[]
        for idx in indices:
            trial=source[['timestamp','value']].copy()
            actual=float(trial.loc[idx,'value'])
            trial.loc[idx,'value']=np.nan
            out,_=recover(trial,minutes=minutes,max_gap=1,method=name)
            pred=out.estimated.iloc[idx]
            if np.isfinite(pred):errors.append(float(pred)-actual)
        rows.append({'method':name,'evaluated':len(errors),'eligible':len(indices),
                     'coverage_pct':round(100*len(errors)/len(indices),1) if indices else 0,
                     'mae':float(np.mean(np.abs(errors))) if errors else None,
                     'rmse':float(np.sqrt(np.mean(np.square(errors)))) if errors else None})
    return rows


def threshold_sensitivity(out, gap, thresholds, method='Newton divided differences'):
    """Re-fit from observed anchors; solve each hypothetical limit with Bisection.
    Deliberately reports estimated crossing, not certified event time.
    """
    ts=pd.to_datetime(out['timestamp'])
    starts=np.flatnonzero(ts==pd.Timestamp(gap['from']))
    ends=np.flatnonzero(ts==pd.Timestamp(gap['to']))
    if not len(starts) or not len(ends):return []
    a=int(starts[0]);b=int(ends[0])
    if a<1 or b>=len(out)-1:return []
    ctx=[i for i in range(max(0,a-2),a)]+[i for i in range(b+1,min(len(out),b+3))]
    ctx=[i for i in ctx if pd.notna(out.value.iloc[i])]
    if len(ctx)<2:return []
    try:p=INTERPOLATORS[method](np.array(ctx,float),out.value.iloc[ctx].to_numpy(float))
    except ValueError:return []
    results=[]
    for limit in thresholds:
        f=lambda z:float(p(z)-float(limit))
        grid=np.linspace(a-1,b+1,301)
        roots=[]
        for u,v in zip(grid[:-1],grid[1:]):
            fu,fv=f(u),f(v)
            if abs(fu)<=1e-8:r=float(u)
            elif fu*fv<0:
                solution=ROOT_SOLVERS['Bisection'](f,float(u),float(v))
                if not solution.converged:continue
                r=solution.root
            else:continue
            if not any(abs(r-old)<1e-5 for old in roots):roots.append(r)
        results.append({'threshold':float(limit),'crossing_count':len(roots),
                        'first_crossing':str(ts.iloc[0]+pd.Timedelta(minutes=(ts.iloc[1]-ts.iloc[0]).total_seconds()/60*min(roots))) if roots else None,
                        'first_crossing_index':float(min(roots)) if roots else None})
    return results
