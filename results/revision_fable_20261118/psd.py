import sys, numpy as np
R='/home/mmggjj/workspace/TFM_ENCRY/results/motor_campana/'
def an(d,T2ns,kd=2,L=16):
    z=np.load(R+d+'/kd02_trozos.npz'); a=np.unpackbits(z["datos"]).reshape(-1,4096)
    x=2.0*a-1; n=4096; j=np.arange(n); nb=n//L
    P=0; fr=[]
    for t in x:
        s=np.abs(np.fft.rfft(t-t.mean(),n*16)); nu=(np.argmax(s[16:])+16)/(n*16.)
        zc=(t*np.exp(-2j*np.pi*nu*j)).reshape(nb,L).mean(1)
        p=np.unwrap(np.angle(zc))/(2*np.pi)
        nn=np.arange(nb); p=p-np.polyval(np.polyfit(nn,p,1),nn)
        f=np.diff(p)            # frecuencia instantanea (ciclos de ro1 por bloque)
        fr.append(f)
        P=P+np.abs(np.fft.rfft(f*np.hanning(f.size)))**2
    P/=len(x); fr=np.array(fr)
    dt=L*2**kd*T2ns*1e-9
    fq=np.fft.rfftfreq(nb-1,dt)
    print(d,'dt bloque %.2f us'%(dt*1e6))
    # PSD de frecuencia: blanco = termico; pico = modulacion
    for i in range(0,40): print('  %7.1f kHz  %.3e'%(fq[i]/1e3,P[i]))
    print('  mediana alta frecuencia (bins 60-120) %.3e'%np.median(P[60:120]))
    # media sincronizada: ¿la modulacion tiene fase fija respecto al inicio del trozo?
    m=fr.mean(0); print('  rms de la media por posicion %.3e frente a rms total %.3e (determinista sincronizada con la captura si es comparable)'%(m.std(),fr.std()))
an(sys.argv[1],float(sys.argv[2]))
