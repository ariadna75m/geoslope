# Verificación de instalación limpia

## Procedimiento realizado

Se creó un ZIP completo y se extrajo en carpeta temporal sin reutilizar entorno virtual ni base. Se creó venv nuevo con Python 3.12.14 en Linux, se instalaron requirements de aplicación y desarrollo, se verificaron artefactos y se inicializó SQLite. Se crearon administrador e ingeniero con contraseñas aleatorias, se configuró TOTP en ambos, se inició sesión y se comprobó denegación administrativa al ingeniero.

Se guardó una revisión sintética, exportaron PDF/CSV/JSON, creó y restauró backup cifrado, reinició el contenedor y confirmó persistencia. Se ejecutaron 258 pruebas, Ruff y recorrido real de navegador Chromium local con bloqueo de conexiones externas. Todo aprobó. El estado temporal fue eliminado; el paquete final no contiene usuarios, claves, sesiones ni DB privada.

## Archivos de evidencia

`clean_install/clean_validation.json`, `clean_install/clean_dependencies.txt`, `clean_install/clean_installation.txt`, `clean_install/clean_database.txt`, `clean_install/clean_workflow.txt`, `clean_install/clean_all_tests.xml`, `clean_install/clean_browser.txt` y `delivery_validation.json`.

El ZIP probado tiene SHA-256 `51bbaf03d33cf2ea30b5021cba2f7b7248b9c1e7f1b1a6eba3eff154bed568a9`. El ZIP final añade informes/capturas, conserva el mismo núcleo de aplicación y modifica solo esperas del script de capturas, verificadas por una nueva ejecución. No se afirma identidad binaria de ambos paquetes.

## Uso en destino

Consultar `docs/manual_instalacion.md`. Python 3.11+; instalar inicialmente dependencias, inicializar DB, ejecutar launcher, abrir loopback y crear administrador/TOTP. Sin credenciales predeterminadas. Conservar completa la estructura superior y todos los artefactos previos.

Windows tiene launcher e instrucciones; no se realizó prueba nativa Windows ni Python 3.11. La ejecución posterior es offline; preparar wheels compatibles si la instalación inicial tampoco tendrá conexión. No se incluye Chromium ni un ejecutable de Windows.

> GeoSlope Review es una herramienta experimental de apoyo. Las anomalías y episodios mostrados no representan predicciones de falla ni niveles de riesgo. Los resultados requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para tomar decisiones operativas o de seguridad.
