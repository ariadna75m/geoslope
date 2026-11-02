# GeoSlope Review 0.7.4 — Relieve integrado

En Vista espacial, activa **Mostrar relieve de Century Mine** para explorar el relieve real en 2D o 3D. La vista 3D permite girar, acercar, restablecer la cámara y cambiar la exageración vertical a 1×, 3× o 5×. Fuente y archivo de relieve permite descargar el GeoTIFF original recortado. Apaga el control para volver a los prismas; se conservan la selección y los filtros. Los filtros instrumentales quedan desactivados mientras se muestra el relieve.

## Alcance de la integración

Se añadió una malla de superficie Copernicus GLO-30 de 216 × 216 muestras, resolución aproximada de 30 m. Se distribuye localmente con la licencia, metadatos, huellas de adquisición y archivo georreferenciado. No se añadieron dependencias Python de geoprocesamiento. La malla compacta se verifica con SHA-256 al cargarla.

La vista 2D conserva longitud/latitud WGS84 y la 3D usa UTM 54S. Las cotas son metros EGM2008 y se conservan las cotas negativas del producto. La exageración cambia la proporción visual, sin modificar las cotas.

Los prismas utilizan una referencia local sin validar. Se muestran en una vista alternativa y no se desplazaron arbitrariamente sobre el relieve. La superposición queda pendiente de conocer su CRS, unidades, datum vertical y puntos de control. Esta superficie no se presenta como un levantamiento fino del talud ni una captura exacta de 2014.

## Verificación

- 285 pruebas generales aprobadas: seguridad, roles, datos, revisiones, reportes y navegación.
- Las nuevas pruebas cubren ambos roles, conservación de cotas, 2D/3D, exageración, rechazo de archivos alterados y retorno a la selección original del prisma.
- Navegador: superficie 3D, plano 2D, descarga del GeoTIFF con igualdad de bytes y regreso a prismas. Sin errores JavaScript ni solicitudes externas.
- Ruff aprobado. Instalación y los 17 archivos congelados verificados.
- 507 archivos de Fases 1–6 comparados con la entrega anterior: ninguno modificado.
- El paquete excluye bases, sesiones, claves, cuentas de prueba y entornos privados.

Evidencia: `reports/phase7/terrain_integration/`. Reproducir la revisión de navegador: `python scripts/validate_terrain.py --chromium RUTA`.

## Uso

Descomprime el paquete completo conservando `monitoreo-taludes/geoslope_review`. Sigue las instrucciones de instalación habituales del README. Si utilizas una instalación existente, conserva una copia de tu carpeta privada de datos y de su clave antes de sustituir los archivos de la aplicación.
