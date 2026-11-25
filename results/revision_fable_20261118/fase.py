import sys, numpy as np
R='/home/mmggjj/workspace/TFM_ENCRY/results/motor_campana/'
def carga(d,f='kd02_trozos.npz'):
    z=np.load(R+d+'/'+f)
    k=list(z.keys()); a=z[k[0]]
    return k,a
def analiza(d,kd=2,L=32,f='kd02_trozos.npz'):
    z=np.load(R+d+"/"+f); a=np.unpackbits(z["datos"]).reshape(-1,4096)
    a=np.asarray(a)
    if a.ndim==1: a=a.reshape(-1,4096)
    if a.shape[1]!=4096 and a.shape[1]==512: a=np.unpackbits(a,axis=1)
    x=2.0*a-1
    n=a.shape[1]; j=np.arange(n)
    # nu global por FFT media
    S=np.abs(np.fft.rfft(x-x.mean(1,keepdims=True),axis=1))**2
    nu0=np.argmax(S.mean(0)[1:])+1; nu0=nu0/n
    nb=n//L
    th=[];nus=[]
    for t in x:
        # nu por trozo: pico FFT con relleno
        s=np.abs(np.fft.rfft(t-t.mean(),n*16)); nu=np.argmax(s[16:])+16; nu=nu/(n*16.)
        z=(t*np.exp(-2j*np.pi*nu*j))[:nb*L].reshape(nb,L).mean(1)
        p=np.unwrap(np.angle(z))/(2*np.pi)
        th.append(p); nus.append(nu)
    th=np.array(th); nus=np.array(nus)
    nn=np.arange(nb)
    # quitar tendencia lineal por trozo
    A=np.vstack([nn,np.ones(nb)]).T
    coef=np.linalg.lstsq(A,th.T,rcond=None)[0]
    res=th-(A@coef).T
    print(d,'trozos',a.shape,'unos %.4f'%a.mean(),'nu0 %.5f'%nu0,'nu trozo: media %.6f sd %.2e'%(nus.mean(),nus.std()))
    ms=[1,2,3,4,6,8,12,16,24,32,48,64]
    D=[]
    for m in ms:
        dd=th[:,m:]-th[:,:-m]
        dd=dd-dd.mean(1,keepdims=True)  # quita frecuencia media del trozo
        D.append((dd**2).mean())
    D=np.array(D); ms=np.array(ms,float)
    # ajuste D = n0 + a m + c m^2
    X=np.vstack([np.ones_like(ms),ms,ms**2]).T
    sel=ms<=16
    w=1/D[sel]
    p=np.linalg.lstsq(X[sel]*w[:,None],D[sel]*w,rcond=None)[0]
    for m,v in zip(ms,D): print('  m %3d (M=%4d muestras) D=%.4e  D/m=%.3e'%(m,m*L,v,v/m))
    print('  ajuste m<=16: suelo %.3e, lineal %.3e/bloque -> Q/muestra %.3e, Q/periodo ro2 %.3e ; cuadr %.3e'%(p[0],p[1],p[1]/L,p[1]/L/2**kd,p[2]))
    # solo lineal+suelo en m<=4
    return
for d in sys.argv[1:]:
    analiza(d)
