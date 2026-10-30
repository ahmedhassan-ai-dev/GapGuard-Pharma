"""Numerical algorithms implemented explicitly for MATH 301; no scipy solvers used."""
from dataclasses import dataclass
import math
import numpy as np

@dataclass
class RootResult:
    method: str
    root: float | None
    iterations: int
    residual: float | None
    converged: bool
    reason: str = ''

def divided_differences(xs, ys):
    x=np.asarray(xs,dtype=float); c=np.asarray(ys,dtype=float).copy()
    if len(x)!=len(c) or not len(x) or len(set(x))!=len(x):
        raise ValueError('Expected equal-size nonempty arrays with unique x coordinates')
    for j in range(1,len(x)):
        c[j:] = (c[j:] - c[j-1:-1])/(x[j:]-x[:len(x)-j])
    return c

def newton_poly(xs,ys):
    x=np.asarray(xs,dtype=float); coef=divided_differences(x,ys)
    def p(t):
        z=np.asarray(t,dtype=float)
        val=np.zeros_like(z)+coef[-1]
        for i in range(len(coef)-2,-1,-1):
            val=val*(z-x[i])+coef[i]
        return float(val) if np.ndim(val)==0 else val
    return p

def lagrange_poly(xs,ys):
    x=np.asarray(xs,dtype=float); y=np.asarray(ys,dtype=float)
    if len(x)!=len(y) or len(x)==0 or len(set(x))!=len(x):
        raise ValueError('Unique x coordinates required')
    def p(t):
        z=np.asarray(t,dtype=float); out=np.zeros_like(z)
        for i in range(len(x)):
            basis=np.ones_like(z)
            for j in range(len(x)):
                if i!=j: basis=basis*(z-x[j])/(x[i]-x[j])
            out=out+y[i]*basis
        return float(out) if np.ndim(out)==0 else out
    return p

def linear_interp(xs,ys):
    x=np.asarray(xs,dtype=float); y=np.asarray(ys,dtype=float)
    order=np.argsort(x); x=x[order];y=y[order]
    if len(x)<2 or len(set(x))!=len(x): raise ValueError('At least two unique x required')
    def p(t):
        z=np.asarray(t,dtype=float)
        if np.any(z<x[0]-1e-9) or np.any(z>x[-1]+1e-9): raise ValueError('No extrapolation')
        val=np.interp(z,x,y)
        return float(val) if np.ndim(val)==0 else val
    return p

def newton_forward_backward(xs,ys,direction='forward'):
    x=np.asarray(xs,float); y=np.asarray(ys,float)
    if len(x)<2 or not np.allclose(np.diff(x),np.diff(x)[0],rtol=1e-7,atol=1e-8):
        raise ValueError('Newton forward/backward requires equally spaced x')
    diffs=[y]
    while len(diffs[-1])>1: diffs.append(np.diff(diffs[-1]))
    h=x[1]-x[0]
    def p(t):
        z=np.asarray(t,float); out=np.zeros_like(z)
        if direction=='forward':
            q=(z-x[0])/h;factor=np.ones_like(z)
            for k,d in enumerate(diffs):
                if k:factor=factor*(q-(k-1))/k
                out=out+factor*d[0]
        elif direction=='backward':
            q=(z-x[-1])/h;factor=np.ones_like(z)
            for k,d in enumerate(diffs):
                if k:factor=factor*(q+(k-1))/k
                out=out+factor*d[-1]
        else:raise ValueError('direction must be forward or backward')
        return float(out) if np.ndim(out)==0 else out
    return p

def bisection(f,a,b,tol=1e-8,max_iter=100):
    fa,fb=f(a),f(b)
    if not all(map(math.isfinite,[fa,fb])):return RootResult('Bisection',None,0,None,False,'Nonfinite endpoints')
    if abs(fa)<=tol:return RootResult('Bisection',a,0,abs(fa),True)
    if abs(fb)<=tol:return RootResult('Bisection',b,0,abs(fb),True)
    if fa*fb>0:return RootResult('Bisection',None,0,None,False,'No sign-change bracket')
    for i in range(1,max_iter+1):
        m=(a+b)/2;fm=f(m)
        if abs(fm)<=tol or abs(b-a)<=tol:return RootResult('Bisection',m,i,abs(fm),True)
        if fa*fm<0:b=m
        else:a=m;fa=fm
    return RootResult('Bisection',m,max_iter,abs(fm),False,'Maximum iterations')

def false_position(f,a,b,tol=1e-8,max_iter=100):
    fa,fb=f(a),f(b)
    if not all(map(math.isfinite,[fa,fb])):return RootResult('False Position',None,0,None,False,'Nonfinite endpoints')
    if abs(fa)<=tol:return RootResult('False Position',a,0,abs(fa),True)
    if abs(fb)<=tol:return RootResult('False Position',b,0,abs(fb),True)
    if fa*fb>0:return RootResult('False Position',None,0,None,False,'No sign-change bracket')
    for i in range(1,max_iter+1):
        if abs(fb-fa)<1e-15:break
        c=(a*fb-b*fa)/(fb-fa);fc=f(c)
        if abs(fc)<=tol:return RootResult('False Position',c,i,abs(fc),True)
        if fa*fc<0:b=c;fb=fc
        else:a=c;fa=fc
    return RootResult('False Position',c if 'c' in locals() else None,max_iter,abs(fc) if 'fc' in locals() else None,False,'Maximum iterations or stagnation')

def secant(f,a,b,tol=1e-8,max_iter=100):
    x0,x1=a,b;f0,f1=f(x0),f(x1)
    for i in range(1,max_iter+1):
        if abs(f1)<=tol:return RootResult('Secant',x1,i-1,abs(f1),True)
        if abs(f1-f0)<1e-14: return RootResult('Secant',x1,i,abs(f1),False,'Zero denominator')
        xn=x1-f1*(x1-x0)/(f1-f0)
        if not math.isfinite(xn) or xn<a-1e-8 or xn>b+1e-8:
            return RootResult('Secant',None,i,None,False,'Iteration left physical interval')
        x0,x1=x1,xn;f0,f1=f1,f(x1)
        if abs(f1)<=tol:return RootResult('Secant',x1,i,abs(f1),True)
    return RootResult('Secant',x1,max_iter,abs(f1),False,'Maximum iterations')

def newton_raphson(f,a,b,tol=1e-8,max_iter=100):
    x=(a+b)/2
    for i in range(1,max_iter+1):
        fx=f(x)
        if abs(fx)<=tol:return RootResult('Newton-Raphson',x,i-1,abs(fx),True)
        h=max(1e-6,(b-a)*1e-5)
        left=max(a,x-h);right=min(b,x+h)
        derivative=(f(right)-f(left))/(right-left) if right>left else 0
        if abs(derivative)<1e-12:return RootResult('Newton-Raphson',x,i,abs(fx),False,'Zero derivative')
        xn=x-fx/derivative
        if not a<=xn<=b:return RootResult('Newton-Raphson',None,i,None,False,'Iteration left physical interval')
        x=xn
    return RootResult('Newton-Raphson',x,max_iter,abs(f(x)),False,'Maximum iterations')

ROOT_SOLVERS={'Bisection':bisection,'False Position':false_position,'Secant':secant,'Newton-Raphson':newton_raphson}
INTERPOLATORS={'Linear':linear_interp,'Newton divided differences':newton_poly,'Lagrange':lagrange_poly,'Newton forward':lambda x,y:newton_forward_backward(x,y,'forward'),'Newton backward':lambda x,y:newton_forward_backward(x,y,'backward')}
