import sys, numpy as np
sys.path.insert(0,'/home/mmggjj/workspace/TFM_ENCRY/analysis')
R='/home/mmggjj/workspace/TFM_ENCRY/results/motor_campana/'
def an(d,T2ns,kd=2,L=16):
    z=np.load(R+d+'/kd02_trozos.npz'); a=np.unpackbits(z["datos"]).reshape(-1,4096)
    x=2.0*a-1; n=4096; j=np.arange(n); nb=n//L
    P=0
    for t in x:
        s=np.abs(np.fft.rfft(t-t.mean(),n*16)); nu=(np.argmax(s[16:])+16)/(n*16.)
        zc=(t*np.exp(-2j*np.pi*nu*j)).reshape(nb,L).mean(1)
        p=np.unwrap(np.angle(zc))/(2*np.pi)
        nn=np.arange(nb); p=p-np.polyval(np.polyfit(nn,p,1),nn)
        f=np.diff(p)
        P=P+np.abs(np.fft.rfft(f))**2/f.size   # sin ventana: PSD = varianza por bloque si blanco
    P/=len(x)
    k=np.arange(P.size); u=4*np.sin(np.pi*k/(nb-1)/1.0*0.5*2/2)**2
    u=4*np.sin(np.pi*k/(nb-1))**2
    dt=L*2**kd*T2ns*1e-9; fq=k/((nb-1)*dt)
    # mediana movil robusta frente a lineas; ajuste P = w + r*u en 80 kHz..1.2 MHz
    sel=(fq>80e3)&(fq<1.2e6)
    # ajuste robusto iterado
    m=sel.copy()
    for _ in range(6):
        A=np.vstack([np.ones(m.sum()),u[m]]).T
        w,r=np.linalg.lstsq(A,P[m],rcond=None)[0]
        res=P-(w+r*u); s=np.median(np.abs(res[m]))*1.5
        m=sel&(res<3*s)
    Qs=w/L; Qp=Qs/2**kd
    print('%-36s unos %.4f blanco %.3e ciclos2/bloque -> Q/periodo ro2 %.2e (K*=2^%.1f); ruido de medida r=%.2e; bins usados %d/%d; potencia total f %.3e, en lineas/baja f %.0f %%'%(d,a.mean(),w,Qp,np.log2(0.2286/Qp),r,m.sum(),sel.sum(),P[1:].mean(),100*(1-(w+r*u[1:]).mean()/P[1:].mean())))
for d,T in [('basys3_jitter_kd02_quieto_bel',4.878),('basys3_jitter_kd02_quieto_bel_r2',4.878),('basys3_jitter_kd02_normal_bel',4.831),('basys3_jitter_kd02_normal_bel_r2',4.831),('basys3_jitter_kd00_02_quieto',7.68),('basys3_jitter_kd00_02_quieto_r2',7.68),('basys3_jitter_kd00_02_normal',7.69),('basys3_jitter_kd02_normal_r2',7.69)]:
    try: an(d,T)
    except Exception as e: print(d,'ERR',e)
import ero_model, inspect
print(inspect.signature(ero_model.min_entropia_analitica))
for q in (1e-6,1.5e-6,2e-6):
    for kd in (14,16,17,18,19,20):
        try: print('Q %.1e kd %d Qbit %.3f Hinf %.4f'%(q,kd,q*2**kd,ero_model.min_entropia_analitica(q*2**kd)))
        except Exception as e: print('ERR',e); break
