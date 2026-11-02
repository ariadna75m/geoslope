> Actualización vigente 0.7.3: sidebar compartido de 88 px, rutas y permisos verificados; 281 pruebas aprobadas. Consulte [shared_sidebar.md](shared_sidebar.md). La evidencia anterior se conserva como historial.


# Validación técnica de Fase 7

**Resultado: aprobada con observaciones.** Fecha de cierre: 2026-10-04.

|Comprobación|Evidencia|Resultado|
|---|---|---|
|Regresión inicial|`../../../reports/phase7/previous_tests.xml`|200 aprobadas|
|Suite conjunta inicial|`all_tests.xml`|258 aprobadas|
|Suite final en venv nuevo|`clean_install/clean_all_tests.xml`|258 aprobadas en 73,41 s; cero errores|
|Pruebas nuevas|58 casos parametrizados: seguridad, integración y UI|58 aprobadas|
|Lint|`clean_install/clean_ruff.txt`|Ruff aprobado|
|Instalación limpia|`clean_install/clean_validation.json`|Dependencias, DB, flujo y navegador aprobados|
|Ambos roles / revisión y reinicio|`clean_install/clean_workflow.txt`|Persistencia y permisos comprobados|
|Navegador local|`browser_validation.json`|12 capturas reales, cero solicitudes externas|
|Artefactos congelados|`final_frozen_verification.json`|426 archivos intactos; predicciones idénticas|
|Reproducibilidad previa|Misma verificación final|12 CSV byte idénticos, IDs y tipos conservados|
|Causalidad|4 pruebas de prefijo en verificación final|732, 3.917, 5.453 y 6.799 filas sin cambios causales|
|Reportes|`example_reports/` y casos de formatos/alcances|PDF/CSV/JSON; tres PDF renderizados y revisados|
|Backups|Casos de integración y workflow limpio|Cifrado, restauración, corrupción rechazada, sesiones revocadas|
|Paquete sin estado privado|Inspección final del ZIP|Sin DB, claves, copias privadas, .venv ni sesiones|

## Alcance de la evidencia

Streamlit comunica navegador y servidor local por HTTP/WebSocket loopback; offline significa ausencia de conexiones externas durante ejecución, no ausencia de comunicación local. Dependencias se instalaron inicialmente con conexión. Se bloquearon conexiones externas en flujo limpio y en navegador.

La prueba limpia fue ejecutada sobre el núcleo final de aplicación, incluida la fuente incrustada de PDF. Después se añadieron documentos/evidencias y se ajustaron esperas/scroll del script de capturas, vuelto a ejecutar. `delivery_validation.json` verifica igualdad del código de aplicación contra los hashes de la prueba limpia. Todos los datos de cuentas sintéticas fueron temporales y eliminados.

Prueba reproducible desde raíz: `PYTHONPATH=geoslope_review python -m pytest -q tests geoslope_review/tests`. No basta ejecutar pytest sin rutas porque la configuración histórica selecciona solo los 200 casos anteriores. Instalar `geoslope_review/requirements-dev.txt` para Ruff y pruebas opcionales de navegador.

No se mide desempeño de predicción de fallas. No hay prueba nativa Windows/Python 3.11 ni certificación de seguridad/geotécnica. Los tests históricos pueden entrenar modelos sintéticos de sus fixtures; la aplicación y verificación de producción no reentrenan artefactos aprobados.

> GeoSlope Review es una herramienta experimental de apoyo. Las anomalías y episodios mostrados no representan predicciones de falla ni niveles de riesgo. Los resultados requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para tomar decisiones operativas o de seguridad.
