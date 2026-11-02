# Monitoreo de taludes — Fases 1 a 5

Diagnóstico, preparación, exploración, características temporales y modelos no supervisados reproducibles de Data.zip. Las Fases 1 a 5 están completas. Los originales y los resultados históricos permanecen intactos. La Fase 6 requiere aprobación formal antes de comenzar.

## Consultar resultados

Abra `reports/Diagnostico_Fase1.md`. El inventario, diccionario por columna, perfiles por prisma y evidencia completa están en `reports/`. Los ocho archivos originales se conservan en `data/raw/`. La copia DAT y el CSV South West representan las mismas mediciones.

## Reproducir el diagnóstico

Python 3.11 o superior. Se ejecutó en Python 3.12.14 con Pandas 2.2.3, NumPy 2.3.5 y pypdf 6.10.0.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate
python -m pip install -r requirements-inspection.txt
python scripts/inspect_phase1.py
python scripts/build_diagnostic.py
```

Después de instalar dependencias, ambos scripts funcionan sin conexión. Solo escriben resultados dentro de `reports/`; leen todas las tablas manteniendo campos originales como texto y calculan fechas/números en memoria para la auditoría. No son módulos de carga/limpieza del MVP futuro.

Los nombres abreviados de mes en inglés son los del export original; ejecutar con locale compatible con estos nombres. Revisar `invalid_timestamps` en `audit.json` si se reproduce en otro entorno.

## Integridad y puntos de control

ZIP original SHA-256: `b0d3eca632c5c7831d391f6f90b4d88b1a7384b3eb596c19ddaaf64147a24d22`.

Las huellas de los ocho originales están en `reports/original_manifest.json`. Se verificaron contra cada entrada del ZIP al extraer y nuevamente al finalizar. Punto de control Git anterior a cambios: `1c7c14e`. El paquete descargable no incluye el directorio interno `.git`; incluye los scripts y resultados revisados.

## Arquitectura prevista

En las siguientes fases: presentación Streamlit; lógica modular en `src/`; datos originales CSV/Excel, resultados SQLite y modelo Joblib. Durante Fase 1 solo se añaden `scripts/` y `reports/` para separar la auditoría de los módulos futuros. No se crean módulos vacíos ni modelos ficticios.

## Límites

En las Fases 1–2 no se disponía de una fecha de falla documentada. El artículo incorporado en Fase 3 documenta 23-02-2014 únicamente como referencia contextual; no aporta etiquetas independientes suficientes para métricas supervisadas. Se mantienen las unidades no documentadas como “requiere validación”. No se deducen voladuras a partir de magnitud, ni se usa el cambio de velocidad del TXT como velocidad de los prismas. Consulte el informe para zonas horarias, huecos, duplicados, bases de referencia y cobertura de eventos.

Este resultado es una señal de apoyo al seguimiento preventivo. No constituye una predicción definitiva de falla ni reemplaza la evaluación del ingeniero geomecánico.


## Fase 2: instalar, ejecutar y probar

Para usar la preparación:

```bash
python -m pip install -r requirements.txt
python scripts/run_phase2.py
```

Para ejecutar todas las pruebas (xlwt se usa únicamente para generar un XLS sintético):

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Todos los comandos se ejecutan desde esta carpeta. Los scripts funcionan sin conexión después de instalar las dependencias. `run_phase2.py` comprueba la integridad antes/después y genera cuatro carpetas distintas: `west_wall`, `south_west`, `rainfall_2013` y `rainfall_2014`. No une fuentes, interpola, calcula velocidades, entrena modelos ni construye interfaz.

La compatibilidad XLSX usa OpenPyXL; XLS usa xlrd. Los valores almacenados en Excel se representan como texto antes del tipado. XLSX conserva fórmulas como texto sin evaluarlas; XLS no recupera fórmulas. Los originales y su formato permanecen en raw.

Lea `reports/phase2/Resultado_Fase2.md`, `quality_comparison.csv`, `summary.json`, `schema_dictionary.csv`, `pytest-output.txt`, `pytest-results.xml` y `reproducibility.json`. Este último documenta la ejecución completa dos veces con salidas idénticas.

## Auditar una fila

1. Busque su `row_id` en `data/processed/<fuente>/row_dispositions.csv`.
2. Compruebe `source_line`, estado, motivo de exclusión, vínculo a fila conservada y posición final.
3. Consulte `original_rows.csv` para el valor fuente y `data.csv` o `excluded_rows.csv` para el valor tipado junto al campo `original__*`.
4. Consulte `transformations.jsonl` para las políticas, estado antes/después y huellas de cada paso.
5. Compruebe `source_sha256` contra `reports/original_manifest.json`.

Los IDs y los resultados son deterministas para los mismos bytes, hoja y parámetros. Al editar cualquier byte del archivo, cambia su huella y los IDs derivados. Las marcas de calidad no son alertas de falla. El mínimo de 20 instantes únicos es operativo, configurable y no geotécnico.

Para reabrir un CSV procesado preservando los campos originales y ceros iniciales:

```python
import pandas as pd
# Capa textual íntegra; tipar posteriormente solo los campos definidos en metadata.
text = pd.read_csv('data/processed/rainfall_2013/data.csv', dtype=str, keep_default_na=False)
assert text['station_id'].eq('029167').all()
rainfall = pd.to_numeric(text['rainfall_mm'], errors='coerce')  # Vacío -> desconocido, nunca 0.
```

Los datos procesados se regeneran con `run_phase2.py` y se incluyen en el paquete descargable. Se excluyen de Git para evitar versionar copias voluminosas; se versionan código, políticas e informes. Punto de control anterior a Fase 2: `2130e29`.


Para comprobar los artefactos ya exportados:

```bash
python scripts/verify_phase2.py
```

Para regenerar y verificar reproducibilidad byte a byte con dos ejecuciones completas:

```bash
python scripts/verify_phase2.py --reproduce
python scripts/build_phase2_report.py
```

`acceptance_checks.json` documenta la conservación de valores originales, partición completa de filas, timestamps ordenados y únicos dentro de cada identificador, y la cadena de huellas antes/después de cada transformación.


## Fase 3: contexto y exploración descriptiva

El artículo adjunto se conserva en `data/context/`. `reports/documentation/article_context.md` incluye referencia APA 7, páginas, evidencia e inferencias. La adenda documental mantiene intactos los informes históricos de Fases 1–2.

Instalación y reproducción desde esta carpeta, con Python 3.11 o superior:

```bash
python -m pip install -r requirements-phase3.txt
python scripts/run_phase3.py
python scripts/verify_phase3.py --reproduce
python scripts/execute_phase3_notebook.py
python -m pytest -q --junitxml=reports/phase3/pytest-results.xml > reports/phase3/pytest-output.txt
python scripts/build_phase3_report.py
```

`run_phase3.py` lee las salidas preparadas de cuatro fuentes y el catálogo/TXT originales independientemente. Solo escribe en `reports/phase3/`; verifica 59 archivos protegidos antes/después. `verify_phase3.py --reproduce` repite el pipeline y compara 15 tablas por SHA-256, valida los 55 PNG/HTML y los archivos anteriores. Omitir `--reproduce` verifica los artefactos sin regenerarlos.

El notebook `notebooks/exploracion_fase3.ipynb` importa funciones de `src/`; contiene salidas ejecutadas. En este entorno el arranque convencional de Jupyter por puertos TCP quedó bloqueado. `execute_phase3_notebook.py` usa IPython en un solo proceso sin puertos, guarda salidas reales y falla si alguna celda tiene errores. En un equipo local también puede abrirse con Jupyter instalado por el usuario.

Abra `reports/phase3/Exploracion_Fase3.html` en un navegador: contiene cinco gráficos integrados y enlaces a los 55 gráficos. Los HTML individuales usan el archivo **local** `interactive/plotly.min.js`; conservarlo junto a ellos. Ninguna visualización requiere internet tras instalar dependencias y descomprimir el proyecto. Consulte `exploratory_findings.md` para estadísticas, selección de prismas, hallazgos, límites y referencias; los perfiles CSV incluyen todos los prismas y un diccionario explica cada indicador.

La selección usa conteos, rangos y desviación estándar muestral con ≥20 instantes; empates por ID. La fecha de falla no interviene. West Wall es movimiento 3D reportado en mm, no trayectoria acumulada validada. South West permanece con unidades por validar. Solo se concatenan los años meteorológicos de una estación; lluvia desconocida permanece desconocida y meses incompletos llevan total parcial. Catálogo UTC y cambios de velocidad sísmica se describen separados de prismas.

Se entregan 75 pruebas satisfactorias, 10 celdas ejecutadas sin errores y evidencia de integridad. No se implementaron ingeniería de características, modelos, detección de cambios, alertas, SQLite ni Streamlit. El checkpoint previo a esta fase es `f64070e`; el final se registra en `reports/phase3/git_checkpoint.txt`.

## Fase 4: características temporales de West Wall

La tabla de características conserva las 7.178 filas y los 49 prismas de la preparación anterior. Tiene 315 columnas: 20 campos de entrada y 295 añadidos, incluidas banderas y trazabilidad. Los cambios negativos y los extremos se conservan. Se calculan cambios, tasas observadas entre mediciones, estadísticas retrospectivas de 24 h/72 h/7 días, tendencias locales, rachas y comparación con el historial estrictamente previo. Las fuentes complementarias y South West permanecen separados.

```bash
python -m pip install -r requirements-phase4.txt
python scripts/run_phase4.py
python scripts/verify_phase4.py --reproduce
python -m pytest -q --junitxml=reports/phase4/pytest-results.xml > reports/phase4/pytest-output.txt
python scripts/build_phase4_report.py
```

Los comandos solo escriben salidas nuevas en `data/processed/phase4/` y `reports/phase4/`; verifican 226 huellas de archivos anteriores. `verify_phase4.py --reproduce` recalcula siete CSV, compara sus bytes, prueba la lectura exacta de la tabla y modifica el futuro en una copia para comprobar que el pasado permanece idéntico. Sin `--reproduce`, verifica huellas y gráficos ya exportados. Los comandos funcionan sin conexión una vez instaladas las dependencias. Se ejecutaron en Python 3.12; requieren Python 3.11 o superior.

Los criterios están en `config/phase4.json`: std muestral con ≥2 valores; ventana suficiente con ≥3 valores, duración ≥25% de su longitud y sin hueco interno >72 h; pendiente con ≥3 timestamps distintos y duración ≥18/42 h; línea base con ≥20 valores **anteriores** y ≥24 h de duración. Las ventanas son **(t−W,t]**, con límite inferior abierto. Los resúmenes de cambios/tasas solo incluyen pares con ambos extremos dentro de la ventana. Una tasa tras un hueco largo sigue siendo un promedio entre extremos y lleva bandera de calidad. Estos criterios no son umbrales de alerta y no utilizaron la fecha de falla.

Los faltantes derivados permanecen NaN con banderas `_available`. Una media disponible con un dato no significa historia suficiente; consultar `has_sufficient_*_history`. Cero, desconocido o hueco prolongado rompe una racha. Los z-scores excluyen el presente de su referencia y quedan desconocidos cuando su dispersión es nula. Ningún score se convierte todavía en alerta. No se interpola, imputa ni asigna frecuencia esperada.

Consulte `reports/phase4/feature_engineering_findings.md`, el diccionario por columna, disponibilidad por grupo/prisma, metadatos, `reproducibility.json` y evidencia Pytest. Hay 17 pares PNG/HTML descriptivos. Abra los HTML de `reports/phase4/interactive/` conservando a su lado `plotly.min.js`; funcionan sin internet. No se creó un dashboard.

Para cargar las 315 columnas conservando tipos, textos originales y precisión numérica:

```python
import json
from pathlib import Path
from src.feature_validation import read_feature_dataset
metadata = json.loads(Path('reports/phase4/phase4_metadata.json').read_text())
features = read_feature_dataset(metadata['feature_dataset'], metadata['feature_dtypes'])
```

Este lector está destinado a la salida auditada de características. El cargador de archivos de entrada mantiene sus límites anteriores (incluido el límite de columnas) y no se modifica para aceptar la tabla derivada.

La tasa observada y la pendiente local son estadísticas en mm/día, **no velocidades físicas validadas del macizo**. El archivo termina el 20-02-2014 y no observa la falla del 23-02-2014 documentada en el artículo. La Fase 4 no incluye modelos, alertas, métricas supervisadas, uniones de fuentes, SQLite o Streamlit. Checkpoint previo: `fef7d06`; el final se registra en `reports/phase4/git_checkpoint.txt` dentro del paquete.

## Fase 5: modelos no supervisados y evaluación temporal

Se conservaron 7.178 filas y 49 prismas; 5.898 filas son elegibles y 1.280 permanecen desconocidas para modelado. Se seleccionaron 17 de 20 candidatos exclusivamente con entrenamiento. La regla transparente y el Isolation Forest global producen scores, percentiles de entrenamiento y marcas **experimentales**, sin alertas operativas ni niveles de riesgo. No se unieron fuentes ni se utilizó la fecha documental de falla para ajustar parámetros.

Consulte `reports/phase5/model_findings.md` (25 secciones), `provisional_recommendation.json`, tablas de sensibilidad, perfiles por prisma, pruebas sintéticas y `reproducibility.json`. La [adenda terminológica](reports/documentation/phase5_terminology.md) establece la formulación vigente: **Características temporalmente válidas, calculadas sin información futura y respetando el orden cronológico.** Esto no demuestra causalidad científica; se conservan los documentos anteriores para auditoría.

Desde esta carpeta, con Python 3.11 o superior compatible (se ejecutó en Python 3.12):

```bash
python -m pip install -r requirements-phase5.txt
# Verificar primero las salidas ya entregadas, sin reentrenar:
python scripts/verify_phase5.py
# Reproducción completa en carpeta temporal y prueba crítica contra fuga:
python scripts/verify_phase5.py --reproduce
python -m pytest -q --junitxml=reports/phase5/pytest-results.xml > reports/phase5/pytest-output.txt
python scripts/build_phase5_report.py
```

Para regenerar únicamente los artefactos de Fase 5:

```bash
python scripts/run_phase5.py
python scripts/verify_phase5.py --reproduce
python scripts/build_phase5_report.py
```

Los comandos leen las fases anteriores y verifican 294 archivos protegidos. La reproducción compara 24 CSV byte a byte y el estado aprendido completo de los modelos; las puntuaciones son idénticas después de recargar. Los tiempos se registran separados de los resultados deterministas. No se debe regenerar una fase histórica sobre sus salidas protegidas antes de verificar esta fase: cambiar sus metadatos rompería su manifiesto de integridad. Los scripts funcionan offline tras instalar las dependencias. No requieren servicios ni credenciales.

La división utiliza cuantiles de los 93 días calendario observados: entrenamiento antes de `2014-01-15 00:00:00`, validación hasta antes de `2014-02-02 00:00:00`, prueba desde ese instante. Días completos y timestamps iguales quedan en un solo periodo. Los porcentajes de filas pueden diferir de 60/20/20. Medianas, RobustScaler, referencias de la regla, árboles y umbrales se ajustan solo con las 2.909 filas elegibles de entrenamiento. El modelo usa 200 árboles, máximo 256 muestras, semilla 42 y contaminación 0,02. La calidad sirve para elegibilidad y contexto, no como predictor del bosque.

Los modelos están en `models/phase5/`: preprocesador, pipeline de Isolation Forest, `scoring_bundle.joblib` para ambos métodos, regla JSON, variables y metadatos. El bundle necesita filas con características y banderas derivadas del historial, no una medición cruda aislada. `src/` debe permanecer importable al recargar. Un ejemplo que usa una fila de las características entregadas:

```python
import json
import joblib
from pathlib import Path
from src.feature_validation import read_feature_dataset
metadata = json.loads(Path('reports/phase4/phase4_metadata.json').read_text())
features = read_feature_dataset(metadata['feature_dataset'], metadata['feature_dtypes'])
bundle = joblib.load('models/phase5/scoring_bundle.joblib')
result = bundle.score_new(features.tail(1))  # No reajusta el modelo.
```

La tabla maestra de puntuaciones es `data/processed/phase5/anomaly_scores.csv`. Para reabrirla preservando NaN y booleanos anulables:

```python
import pandas as pd
metadata = json.loads(Path('reports/phase5/phase5_metadata.json').read_text())
result = pd.read_csv('data/processed/phase5/anomaly_scores.csv',
                     dtype={k: v for k, v in metadata['score_dtypes'].items() if v != 'datetime64[ns]'},
                     parse_dates=['timestamp'], float_precision='round_trip')
```

Las filas no elegibles no son normales: sus scores, percentiles y marcas permanecen desconocidos. q95/q98/q99 y el umbral interno son referencias técnicas distintas. Las explicaciones son desviaciones descriptivas aproximadas, no contribuciones exactas de Isolation Forest. Sin etiquetas confiables no se calculan métricas supervisadas sobre datos reales. Los 14 ensayos artificiales usan copias de validación y están separados de la tabla real; sus resultados no validan predicción de fallas.

Los 20 pares PNG/HTML están en `reports/phase5/figures/` e `interactive/`. Los HTML requieren su `plotly.min.js` local junto a ellos. No se construyó un dashboard. Checkpoint inicial de Fase 5: `11c2a12`; el hash final está en `reports/phase5/git_checkpoint.txt` dentro del paquete. Se espera aprobación formal antes de iniciar la Fase 6.

### Revisión específica de `max_features`

La auditoría confirmó que la configuración y el Joblib anteriores ya tenían `max_features=1.0` **float**, con 17 características disponibles en cada uno de los 200 árboles. La tabla anterior del informe mostraba `1` al quitar decimales; se corrige esa presentación y se valida explícitamente el tipo. No se afirma un cambio inexistente de entero a float en el artefacto histórico. Se reentrenó el principal y se recalcularon sus resultados, que permanecen numéricamente idénticos.

Se añade una comparación controlada nueva: `1` entero → 1 variable por árbol; `0.5` float → 8; `1.0` float → 17. Mantiene el mismo entrenamiento, selector, imputador y escalador congelados, árboles, muestras, contaminación y semilla; cada variante obtiene umbrales únicamente de entrenamiento. `max_features_sensitivity.csv` cubre los rankings top 1/2/5%, scores, marcación, concentración, distancia KS y carga diaria; las tablas auxiliares conservan observaciones, perfiles y nombres disponibles/usados por árbol. `max_features_synthetic_results.csv` compara los mismos 14 escenarios sin modificar sus inyecciones ni reajustar durante los ensayos.

`seed_rank_changes.csv` y `seed_prism_instability.csv` documentan variación de posición entre las cinco semillas, siempre con principal float 1.0. `prism_30_1994_max_features.csv` revisa su concentración sin eliminar extremos. El informe previo y su hash están en `reports/phase5/audit/`; checkpoint anterior: `8411a6306bebf2d2f18160f5511eb577a28ffca9`. Usar 17 variables disponibles no demuestra mejor precisión ni validez geomecánica. Se mantiene pendiente la aprobación formal para Fase 6.
