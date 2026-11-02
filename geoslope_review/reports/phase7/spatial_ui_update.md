# Vista espacial actualizada — GeoSlope Review 0.7.1

## Resultado

Se adaptó la pantalla a la referencia entregada: espacio oscuro, filtros a la izquierda, escenario interactivo central y ficha/serie del prisma a la derecha. Se conserva el resto del sistema y sus permisos.

Funciones: búsqueda, filtros por estado estadístico, solo candidatos, etiquetas, fecha de corte, vistas 2D/3D, selección, centrado en prisma y restablecimiento del encuadre. El centrado cambia la cámara/rango visual, sin modificar puntos. La ficha muestra coordenadas originales, última medición, episodios iniciados y filas candidatas hasta el corte; serie vinculada con marcas congeladas. La tabla expandida conserva resúmenes retrospectivos de Fase 6, señalados por separado.

## Lo que permiten los archivos

`Data.zip` contiene tres archivos de desplazamiento de prismas, eventos/voladuras, cambios de velocidad sísmica y meteorología. No contiene DEM, ortofoto, malla ni nube topográfica. Los CSV principales incluyen Easting/Northing/RL, pero el sistema de referencia, unidades y datum siguen sin aprobación. La imagen de referencia es un diseño, no un terreno georreferenciado utilizable.

El artículo incluye figuras de contexto; una figura impresa no proporciona por sí sola la geometría y transformación necesarias para posicionar estos prismas sobre una mina real. No se extraen relaciones espaciales ni modelos del evento posterior al dataset.

## Para mostrar un escenario real como el de referencia

- Vista 2D: ortofoto georreferenciada del sector y transformación aprobada al sistema de los prismas.
- Vista 3D: DEM, nube de puntos o malla topográfica real, con unidades, CRS/datum, fecha y cobertura conocidas; textura real si se busca apariencia fotográfica.
- Si las coordenadas son locales, relación validada con la referencia del terreno o puntos de control suficientes.

Hasta disponer de esos insumos se presenta únicamente la geometría instrumental original. `Centrar en prisma` lleva al punto dentro de ese espacio; no constituye navegación GPS, ubicación sobre fotografía ni reconstrucción del talud. No se generan bancos, isolíneas o elevaciones artificiales.

## Validación

**262 pruebas aprobadas:** 258 anteriores y cuatro nuevas de coordenadas, centrado 2D/3D, escena vacía y controles de interfaz. Ruff aprobado. Navegador real local: ambos modos, centrar/restablecer, filtros, ficha y gráficos, autenticación, revisión, PDF, backup y logout; cero solicitudes externas.

Se compararon 507 archivos anteriores fuera de la aplicación contra el ZIP base: todos idénticos byte a byte. Manifiesto congelado aprobado; se conservan 7.178 registros, 49 prismas, 48 episodios y 102 candidatos híbridos. No se modifica política, umbrales, scores ni modelos.

Capturas reales: `screenshots/07_espacial.png`, `13_espacial_centrada.png` y `14_espacial_2d.png`. Se revisaron visualmente; no son imágenes generadas de una supuesta mina. Cuentas de prueba temporales retiradas; QR oculto en capturas.

La instalación limpia completa del paquete base 0.7.0 ya estaba validada. Esta actualización se verificó con dependencias instaladas en un venv nuevo y suite/navegador; no se presenta como repetición de extracción e instalación limpia del ZIP actualizado. Windows/3.11 y evaluación geotécnica siguen pendientes.

## Alcance

Versión 0.7.1 con mejora de presentación y navegación instrumental, sujeta a las limitaciones documentadas. Requiere revisión especializada; las anomalías no son predicciones de falla ni niveles de riesgo.
