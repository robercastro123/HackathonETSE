# HackathonETSE

## Convertir las preguntas y ejecutar el quiz

Con Python 3, desde esta carpeta:

```bash
python3 csv_a_json.py preguntas.csv preguntas.json
python3 main.py
```

El conversor admite el formato del CSV incluido: `Categoría`, `Pregunta`,
`Correcta`, `Incorr1`, `Incorr2` e `Incorr3`. También admite CSV con cuatro
columnas de opciones (`opcion_a` a `opcion_d`) y `respuesta_correcta`.
Las filas sin pregunta se ignoran. Las opciones se mezclan de forma estable
para cada pregunta, y el índice de la respuesta correcta se guarda en el JSON.

`main.py` carga `preguntas.json` desde la misma carpeta. Si se modifica el CSV,
vuelve a ejecutar el conversor antes de iniciar el quiz.
