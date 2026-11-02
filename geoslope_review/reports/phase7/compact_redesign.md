# GeoSlope Review 0.7.2 — rediseño compacto de la vista espacial

**Resultado: aprobado con observaciones de datos y plataforma.** Fecha: 2026-10-04. La entrega implementa la distribución de la referencia mediante controles funcionales y datos reales. La captura adjunta de referencia se utilizó para proporciones y jerarquía; sus números, unidades y terreno no se incorporaron.

## Distribución y comportamiento

- Barra de navegación de 78 px, iconos, etiquetas breves, tooltips y opción activa. Las opciones administrativas dependen del rol autorizado por el servidor. Usuario y salida quedan al pie; el perfil conserva la implementación existente.
- Encabezado compacto con título, estado Offline, verificación de archivos y menú del usuario. Estos indicadores informan disponibilidad, no condiciones geotécnicas.
- Fecha, búsqueda por identificador, estado, Solo candidatos, etiquetas, selector 2D/3D y limpieza en una barra horizontal. La búsqueda se confirma con Enter. La selección se conserva mientras siga siendo válida.
- Escena principal y ficha en proporción 2,75:1. Se comprobó al menos 60% del ancho útil para la escena en 1366×768, 1440×900 y 1920×1080, sin desbordamiento horizontal.
- Selección real mediante eventos de Plotly en 2D y 3D; sincronización del selector y la ficha. La cámara permanece durante la actualización parcial. Centrar modifica rangos y cámara, conservando las coordenadas originales. Vista completa restablece la cámara. Pantalla completa local disponible si el navegador la habilita, con entrada y salida comprobadas mediante el botón.
- Ficha compacta con estado, elegibilidad, coordenadas, última observación, episodios, registros candidatos, serie del prisma y acciones. Ver historial abre el prisma correcto; Revisar episodio abre el episodio relacionado. El resumen de episodios se calcula de las filas conocidas al corte. La lectura del episodio terminado en la bandeja mantiene el resumen retrospectivo aprobado.
- Estado inicial sin selección. Hay mensajes para filtros sin resultados y falta de mediciones/episodio, e información de calidad y disponibilidad del modelo. Errores de consulta se presentan sin trazas internas.
- La ficha puede ocultarse desde el menú del usuario. Por debajo de 1100 px se habilita la contracción de navegación y redistribución de filtros. La validación visual formal se limita a las tres resoluciones solicitadas.

## Datos y límites

Se conservan 7.178 registros, 49 prismas, 5.898 evaluables, 1.280 no evaluables, 48 episodios y 102 registros híbridos en 20 episodios. No se cambiaron coordenadas, identificadores, puntajes, umbrales, política, modelos o resultados de Fase 6.

Los ejes representan Easting, Northing y RL originales. El CRS y las unidades espaciales no están validados: no se añade la unidad metros ni se realiza una transformación geográfica. La serie temporal utiliza el campo aprobado `reported_3d_movement_mm`, sin rellenar mediciones faltantes. Calidad se identifica separadamente de las marcas estadísticas; la forma y el texto acompañan al color.

La leyenda agrupa visualmente marca aislada y episodio en observación como Marca estadística; el estado causal original se conserva en los datos y la ficha. Ninguna clasificación geotécnica se deriva de los colores. No existe topografía suficiente; se muestra una franja de una línea y únicamente puntos instrumentales. No se reconstruye una superficie a partir de prismas. El prisma 30-1994 conserva su advertencia de presencia exclusiva en entrenamiento.

## Archivos de implementación

|Archivo|Cambio|
|---|---|
|`app.py`|Navegación compacta y página activa persistente al alternar entre navegación compacta y estándar.|
|`gsreview/presentation/spatial_workspace.py`|Nueva vista modular, ficha vinculada, filtros, errores y actualización parcial.|
|`gsreview/presentation/spatial_controller.py`|Filtrado y validación de eventos de selección.|
|`gsreview/presentation/spatial_component.py`|Adaptador del visor Plotly local.|
|`gsreview/application/spatial.py`|Servicio de lectura autorizado y eventos de acceso usando la auditoría existente.|
|`gsreview/presentation/charts.py`|Símbolos, selección, cámara y minigráfico con datos originales.|
|`gsreview/presentation/views.py`|Integración y enlaces a historial/episodio; navegación del botón de pendientes.|
|`assets/spatial.css`, `assets/logo_mark.svg`|Distribución, estilos acotados y marca local.|
|`assets/spatial_component/index.html`, `plotly.min.js`, `LICENSE_PLOTLY.txt`|Interacción local 2D/3D, pantalla completa y renderer con licencia MIT, sin CDN.|
|`config/app_config.yaml`, `pyproject.toml`|Metadatos de versión 0.7.2.|
|`tests/test_spatial_redesign.py`|Siete pruebas nuevas de controles, autorización, selección y navegación.|
|`tests/test_phase7_spatial_workspace.py`, `tests/test_phase7_ui.py`|Adaptación de pruebas a controles y selección inicial nuevos.|
|`scripts/validate_browser.py`|Clic real 2D/3D, filtros, pantalla completa, resoluciones y regresión de flujo.|
|`README.md`, `docs/manual_usuario.md`, `reports/phase7/`|Documentación, capturas y evidencia actualizadas.|

No se modificaron el código de autenticación/TOTP, reglas de roles, servicios de revisión/reportes/copias, esquema ni acceso a la base de datos. El servicio espacial utiliza las interfaces existentes y añade eventos autorizados de acceso a la vista y apertura de episodio; no se registra cada movimiento de cámara. No se agregaron dependencias Python.

## Validación reproducible

**269 pruebas aprobadas: 262 existentes y 7 nuevas.** Se ejecutó la suite conjunta completa, sin omitir las pruebas históricas. Evidencia: `compact_all_tests.txt` y `compact_all_tests.xml`. Ruff aprobado: `compact_ruff.txt`.

```bash
PYTHONPATH=geoslope_review python -m pytest -q tests geoslope_review/tests
cd geoslope_review
python scripts/verify_installation.py
python scripts/validate_browser.py --chromium /ruta/a/chromium --output reports/phase7/compact_redesign/screenshots
```

La validación en navegador utilizó cuentas y DB sintéticas temporales. Comprobó bootstrap, TOTP, selección real, filtros, cambio de vista, tres resoluciones, pantallas por rol, revisión persistida, PDF, copia cifrada y cierre de sesión. Se bloquearon y registraron solicitudes externas: **cero**. El renderer y sus recursos se sirven desde el equipo local. Las dependencias requieren instalación inicial; offline describe la ejecución posterior.

Verificación byte a byte contra 0.7.1: **507 archivos de Fases 1–6 intactos** y **17 archivos protegidos del núcleo de aplicación intactos**. Los **17 artefactos del manifiesto congelado** conservan sus hashes. No se ejecutó entrenamiento; los modelos y los resultados previos permanecen idénticos. Evidencia: `compact_preservation.json`, `compact_integrity.json` y `compact_redesign_validation.json`.

Las capturas son de la aplicación en funcionamiento y contienen únicamente datos del proyecto y una cuenta sintética. La hoja `screenshot_overview.png` permite inspeccionar estados y resoluciones.

## Capturas

- [Vista 3D](compact_redesign/vista_espacial_3d.png)
- [Vista 2D](compact_redesign/vista_espacial_2d.png)
- [Prisma seleccionado y centrado](compact_redesign/prisma_seleccionado.png)
- Resoluciones, estado vacío, filtros y flujo completo: `screenshots/`.

## Observaciones pendientes

Validar con el especialista el contexto instrumental, CRS y unidades, y aportar topografía documentada si se desea una superficie o navegación geográfica. Este visor localiza puntos dentro del sistema de coordenadas original; no ofrece una ruta sobre un mapa georreferenciado. La comprobación actual se ejecutó en Linux con Python 3.12.14. Windows y Python 3.11 requieren comprobación nativa. La instalación limpia desde ZIP documentada para 0.7.0 se conserva como evidencia histórica; no se atribuye al ZIP 0.7.2 una repetición de esa comprobación.

Los candidatos no son predicciones de falla, no representan niveles de riesgo y requieren revisión de un especialista geotécnico. No deben utilizarse por sí solos para decisiones operativas o de seguridad.
