# Revisión independiente de los problemas abiertos de la Basys 3 (18-11-2026)

Un agente revisor (otro modelo, Fable 5.2), solo lectura, recibió los seis
problemas abiertos sin las recomendaciones de la sesión. Scripts suyos, de
solo lectura sobre capturas ya guardadas (los `.npz` de trozos son locales,
no versionados):

- `fase.py`: demodula la fase de ro1 en cada trozo de 4 096 bits (`kd 2`) y
  calcula la varianza de la diferencia de fase frente al retardo.
- `psd.py`: espectro de la frecuencia instantánea por trozo (bloques de 16
  bits; a `kd 2` con ro2 a 205 MHz, 0,31 µs por bloque, resolución 12,6 kHz).
  Uso: `python psd.py <carpeta de motor_campana> <periodo de ro2 en ns>`.
- `suelo.py`: intento de ajustar el suelo blanco; **no resultó robusto**
  (valores inestables, alguno negativo).

Estimadores **sin validar con bits simulados**.

## Lo que dice (resumen)

1. La varianza de la diferencia de fase no es monótona (sube hasta 0,102
   ciclos² a 768 muestras y baja a 0,055 a 1 536 en la silenciosa con
   `ro_bel.xdc`): no es un paseo aleatorio. Hay una **raya a ~38 kHz** en la
   frecuencia relativa de los anillos (×160 sobre el suelo) y otra hacia
   440-480 kHz. Explicaría el residuo del modelo, la b ≈ 2 y el ×3 entre
   métodos. Hipótesis sin comprobar: el sondeo I2C (400 kHz / 9 ≈ 44 kHz).
2. El suelo blanco (jitter térmico) no se resuelve; cota Q ≲ 1,1·10⁻⁶ por
   periodo de ro2 (σ ≲ 6 ps). Con eso `ero_model` da H_∞ ≈ 0,57 a `kd 16`,
   0,87 a `kd 17`, 0,99 a `kd 18` [ESTIMADO]: **`CFG_KD` ≥ 16 no sería
   conservador**; propone ≥ 18-19 provisional.
3. Biestable del integrado: alargar ro1 a 11-13 etapas antes que ro1/2
   (evidencia SPICE ya hecha; ro1/2 añade un biestable T a 2,7 GHz sin
   caracterizar); H ≈ 0,66-0,72 [ESTIMADO]; Monte Carlo con ff a −40 °C y
   1,32 V añadida.
4. `G_KD_MIN` = 23 en el integrado (25 con ro1 largo): es seguridad, porque
   `CFG_KD` se escribe por I2C. Un test de autocorrelación en línea no
   protege (a `kd 10`, ρ₁ = 0,053 queda a 1,7σ en 1 024 bits).
5. Restricción de ro2 a ~4,5 ns en compilaciones nuevas y comprobación en
   `build.tcl` del camino frente a 0,9 × periodo medido.
6. Repetir los reinicios con `ro_bel.xdc` por coherencia de H_I.
7. En el integrado, el contador de 24 bits a 2,73 GHz no tiene análisis de
   tiempos (`docs/sintesis_resultados.md`); decidir junto con el punto 3.

## Comprobación de la sesión

`psd.py` repetido sobre `basys3_jitter_kd02_quieto_bel` y `_r2`: pico en el
bin de 37,7 kHz de 1,130 y 1,139 frente a ~7·10⁻³ entre 100 y 400 kHz, y
segundo pico a 477 kHz; la media sincronizada con el inicio del trozo es
pequeña (rms 6,9·10⁻⁴ frente a 3,2·10⁻²): la modulación no está en fase con
el arranque de la captura. Repetible; **no** comprobados el origen ni la
cota del suelo. Tareas en `docs/basys3.md`, "Tareas pendientes".
