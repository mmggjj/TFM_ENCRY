# Normas del TFM y cómo cumple esta memoria

Fuente: asignatura "Trabajo Fin de Máster" del Máster en Microelectrónica en
Enseñanza Virtual (curso 2026-27, `202627_50990014-M099`), revisada el
10-10-2026. Los ficheros descargados están en local en
`docs/asignatura_tfm/` (no se suben al repositorio público: son material
del campus). Sin anuncios publicados a esa fecha.

| Fichero del campus | Qué es |
|---|---|
| `Normativa_Trabajos_Fin_de_Estudios.pdf` | Normativa de TFE de la Facultad de Física (BOUS 5/2019) con todos sus anexos |
| `AnexoIb__Formato_Memoria_Directrices_Eval_TFM…pdf` | Formato de la memoria y reparto de la nota |
| `AnexoVIb__Informe_Tutor_TFM.pdf` | Informe que rellena el tutor |
| `Portada_TFM_Cover_LaTeX.zip`, `Portada_TFM_Cover_Word.docx` | Portada oficial |
| `Video formateo Mendeley Cite.pdf` | Enlace a un vídeo del CRAI sobre citas con Mendeley (opcional; aquí se usa BibTeX) |

## Datos del TFM (acuerdo tutor-alumno firmado el 9-10-2026)

- **Título:** *Diseño y caracterización de aleatoriedad de un TRNG basado
  en osciladores en anillos* / *Design and randomness assessment of a Ring
  Oscillator-based TRNG*.
- **Tutores:** asignados; sus nombres no se ponen todavía.
- Cambiar el título exige el Anexo IV.B con 3 meses de antelación a la
  entrega (1 mes si es solo un matiz que no cambia el tema).

## Calendario 2026-27

| Convocatoria | Entrega | Defensa |
|---|---|---|
| Primera | 16 de junio de 2027 | semana del 28 de junio de 2027 |
| Segunda | 7 de julio de 2027 | semana del 19 de julio de 2027 |
| Segunda extendida y tercera (curso 2027-28) | sin fijar | sin fijar |

## La memoria

- Español o inglés, **elegido de común acuerdo entre tutor y alumno**
  (normativa, art. 2.1). Esta memoria está en inglés: hay que confirmarlo
  con los tutores.
- A4, **sin límite de páginas** (el límite de 50 páginas es solo para TFG).
- Apartados que pide el Anexo I.b, a modo ilustrativo, y dónde están aquí:

| Apartado pedido | En esta memoria |
|---|---|
| Portada | portada oficial del máster (`tfm_main.tex`, mismo logo y bloques que `caratulaMasterMicroelectronica.sty`) |
| Índice de contenidos | `\tableofcontents` |
| Introducción | capítulo 1 |
| Motivación y objetivos | capítulo 1, secciones *Motivation* y *Objectives* |
| Metodología y desarrollo de contenidos | capítulo 1 (*Methodology*) y capítulos 2 a 7 |
| Conclusiones | capítulo 8 (aún vacío) |
| Referencias | bibliografía IEEEtran |

La plantilla oficial de portada es para la clase `article` y deja los
textos de muestra fijos ("Título / Title", "Autor / Author"): no rellena
`\titulo`, `\autor` ni `\fecha`. Por eso la portada se ha reconstruido en
`tfm_main.tex` con el mismo logo (`figures/logoUS_IMSE.png`), los mismos
bloques y tamaños, y los datos reales.

## Evaluación

- **30 % tutor** (Anexo VI.b: entendimiento del problema, manejo de la
  bibliografía, dominio de lenguajes y herramientas, generación de ideas
  nuevas, autonomía y dedicación, de 1 a 5; propone una nota de 0 a 10).
- **70 % comisión**: tres profesores del máster; el tutor no forma parte.
- Escala: suspenso < 5; aprobado 5-6,9; notable 7-8,9; sobresaliente 9-10;
  matrícula de honor por unanimidad.
- Guía de lo que se mira (Anexo I.a, escrito para TFG pero orientativo):
  claridad y estructura; contexto científico; motivación, objetivos,
  procedimiento, resultados y conclusiones; metodología adecuada y
  opciones analizadas; figuras numeradas, con pie, citadas y con valor;
  resultados discutidos con coherencia; resumen; bibliografía actual,
  variada y bien citada; madurez científica; ortografía. Y en el curso:
  reuniones con el tutor, planificación, esquema de la memoria antes de
  redactarla, casos de solución conocida para probar el código propio
  (aquí: vectores oficiales, datos sintéticos de Q conocida).

## Entrega y defensa

- **Depósito** en la Secretaría de la Facultad de Física, como mínimo 15
  días naturales antes del periodo de defensa: **3 ejemplares en papel y
  3 copias electrónicas (CD o pen-drive plano) en PDF**, con el **Anexo
  V.B** firmado: declaración de no plagio, y SÍ/NO a defensa en inglés, a
  defensa telemática, a depósito en la Biblioteca, a publicación en idUS
  si saca sobresaliente o matrícula, y a que el tribunal se quede los
  ejemplares.
- **Informe del tutor** (Anexo VI.b) con propuesta de nota.
- **Defensa pública en castellano**, salvo solicitud justificada al
  coordinador del máster en el momento de la entrega (otro idioma o a
  distancia). **Exposición de 30 minutos como máximo** y unos 30 minutos
  de preguntas.
- Se puede adjuntar una fe de erratas antes de la defensa.

## Pendiente para alinear del todo

1. Confirmar con los tutores el idioma de la memoria (inglés) y el de la
   defensa (castellano por defecto).
2. Reenfocar resumen, *abstract* e introducción hacia el título acordado:
   el TRNG y su caracterización en primer plano y el motor criptográfico
   como aplicación y vehículo de verificación.
3. Escribir el capítulo 8 (conclusiones) y los apéndices.
4. Preparar la presentación de 30 minutos.
