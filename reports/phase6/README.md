# Fase 6 — ejecución local

Esta fase organiza las puntuaciones ya guardadas. No entrena modelos ni construye una interfaz.
Requiere Python compatible con los artefactos de Fase 5; versiones exactas en `phase6_metadata.json`.

Desde la raíz del proyecto:

```bash
python -m pip install -r requirements-phase5.txt -r requirements-dev.txt
python scripts/run_phase6.py
python scripts/verify_phase6.py
python -m pytest -s --junitxml=reports/phase6/pytest-results.xml > reports/phase6/pytest-output.txt
python scripts/build_phase6_report.py
```

Una vez instaladas las dependencias, los cuatro últimos comandos funcionan sin internet.
La ejecución inicial y la suite anterior están registradas en `initial_verification.json` y `pytest-before.xml`.
Se protege cada archivo existente mediante `protected_before_phase6.json`; las Fases 1–5 no se reescriben.

`config/phase6.json` contiene ventana principal 72 h, mínimo 2 y política híbrida;
el análisis también incluye 24/48 h y mínimo 3. No usa la fecha de un evento físico.
Los umbrales exactos se leen del JSON de Fase 5, no de sus valores redondeados.

Los CSV están en `data/processed/phase6/`. Los episodios se construyen por prisma,
incluyen únicamente información disponible hasta cada registro y no se reinician en
las fronteras entre entrenamiento, validación y prueba. `episodes.csv` es retrospectivo;
`review_candidates.csv` mantiene estados causales y todas las columnas originales.

La causalidad de la agrupación está condicionada a marcas congeladas. Los scores
de entrenamiento son retrospectivos: el modelo se ajustó al final de ese periodo.
`model_available_at_observation` distingue esas filas de validación/prueba;
no se presenta entrenamiento como simulación de operación en su fecha histórica.

Para inspección gráfica, abra los PNG o los HTML de `interactive/` manteniendo
`plotly.min.js` en esa misma carpeta. No se necesita servidor ni conexión.

Antes de completar la plantilla profesional, guarde una copia fuera de la carpeta
de salidas generadas: `run_phase6.py` vuelve a generar una plantilla con campos humanos vacíos.
Valores sugeridos de estado humano: Pendiente, Revisado, Requiere más información.
Los campos de relevancia, comentarios, seguimiento, revisor y fecha se completan solo por el especialista.

Todos los candidatos son señales estadísticas experimentales para revisión:
no son predicciones de falla, no representan niveles de riesgo y no deben utilizarse
por sí solos para tomar decisiones operativas o de seguridad.
