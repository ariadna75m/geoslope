> Actualización vigente 0.7.3: sidebar compartido de 88 px, rutas y permisos verificados; 281 pruebas aprobadas. Consulte [shared_sidebar.md](shared_sidebar.md). La evidencia anterior se conserva como historial.


# Fase 7 — GeoSlope Review 0.7.0

## Estado y objetivo

**Aprobada con observaciones técnicas.** Se implementó una aplicación funcional offline de apoyo a la revisión especializada; Windows y Python 3.11 requieren comprobación nativa posterior. No se declara validación geotécnica de la política ni de sus candidatos.

## Entradas y hechos verificados

Se conservaron las Fases 1–6 completas. Se leen los cinco CSV aprobados de Fase 6, su esquema en `phase6_metadata.json`, las coordenadas y variables originales de Fase 4 y los modelos/artefactos serializados de Fase 5. El manifiesto de Fase 7 verifica los archivos esenciales antes de importar y al detectar cambios. Importación idempotente, con rechazo de datos incompatibles; no reemplaza automáticamente datasets ni revisiones.

|Resultado congelado|Cantidad|
|---|---:|
|Registros / prismas|7.178 / 49|
|Evaluables / no evaluables|5.898 / 1.280|
|Características|17|
|Marcas de unión / coincidencias|136 / 66|
|Episodios / prismas con episodios|48 / 33|
|Registros híbridos / episodios híbridos / prismas híbridos|102 / 20 / 17|
|Marcas no seleccionadas|34|
|Episodios con interrupciones de calidad|4|

La política permanece: coincidencia en el registro actual **o** registro marcado con al menos dos marcas de unión del mismo prisma en las últimas 72 horas. Conserva reducción de filas del 25% frente a la unión. Umbrales exactos: 4.439772224885318 y 0.5872931971929567; se redondean solo al presentar. No se utilizan eventos fuera del periodo para configurar la aplicación.

## Arquitectura y decisiones técnicas

Monolito modular de cinco capas, servicios de aplicación, repositorio SQLAlchemy, DTO Pydantic y MVC adaptado a Streamlit. Un controlador central protege diez vistas; se evita navegación por URLs de páginas independientes sin guard. Dominio sin dependencia de Streamlit, SQLite ni Plotly. SQL confinado a infraestructura. SQLite contiene 15 tablas, relaciones, índices, transacciones, control de versión de esquema e historial de revisión. Los binarios de modelos se conservan fuera de SQLite.

Nombre, versión, subtítulo y colores están centralizados. Se incluyen fuentes locales, recursos, estilo azul marino/turquesa/morado/gris y gráficos con símbolos y texto. Las pantallas son Inicio, Bandeja, Espacial, Prismas, Calidad, Reportes, Usuarios, Auditoría, Backups y Perfil; el detalle y formulario de episodio están integrados en la bandeja.

## Funciones implementadas

Primera configuración de administrador sin credenciales predeterminadas; contraseña Argon2id, TOTP local y diez códigos de recuperación de un uso. Roles administrador/ingeniero, restricciones repetidas en servicios, bloqueo y espera progresiva, expiración por inactividad, invalidación de sesiones, recuperación y administración segura. La auditoría es de solo adición para la aplicación y está protegida mediante triggers; el control del sistema operativo queda fuera de esa garantía.

Revisiones humanas con relevancia, comentario, calidad y seguimiento; autor/fecha e historial transaccional con detección de conflictos de versión. Los campos profesionales no se completan automáticamente. Reportes general/prisma/episodio en PDF, CSV y JSON con parámetros, evidencia e historial humano. Backups cifrados con validación, copia previa a restaurar, conservación de auditoría y revocación de sesiones.

## Espacio, tiempo y calidad

Se usan Easting, Northing y RL originales unidos por identificador de registro y corroborados contra prisma y fecha. Vistas 2D y 3D seleccionan la última observación disponible hasta la fecha elegida. No se atribuyen unidades, CRS ni datum no aprobados; no se asumen coordenadas geográficas. No existen datos suficientes para terreno, DEM o isolíneas, por lo que se presenta la nube de puntos y el aviso correspondiente. La selección enlaza series reales y episodios.

La aceleración no existe entre las variables congeladas y se informa como no disponible. No se inventa a partir de transformaciones nuevas. El prisma 30-1994 conserva el aviso de presencia exclusiva en entrenamiento y sus 15 marcas por ambos métodos. Los estados de entrenamiento son retrospectivos; causalidad de agrupación condicionada a marcas congeladas. No evaluables, huecos y cuatro interrupciones siguen visibles; ausencia de datos no equivale a estabilidad.

## Validación ejecutada

Las 200 pruebas anteriores se ejecutaron antes de implementar y aprobaron. La suite final y la instalación limpia aprueban 258 pruebas: 200 anteriores y 58 nuevas. Ruff sin incidencias. Se verificaron autenticación, permisos de ambos roles, revisiones tras reinicio, PDF/CSV/JSON, backup/restauración, rechazo de corrupción, hashes, datos espaciales y vistas protegidas.

El ZIP se extrajo en una carpeta temporal, se creó un entorno virtual nuevo, se instalaron dependencias y se ejecutó el flujo completo. Prueba de navegador Chromium local: 12 capturas reales, recorrido de vistas, guardado, descarga PDF, backup y cierre; cero solicitudes externas. La prueba local permite HTTP/WebSocket loopback necesarios para Streamlit. Instalación inicial sí usa internet para dependencias.

La comprobación final protege 426 archivos anteriores, conserva predicciones de Fase 5 y reproduce 12 CSV byte a byte, con entrenamiento bloqueado durante la verificación. No se ejecuta entrenamiento de producción en Fase 7. Se renderizaron y revisaron visualmente los PDF de ejemplo y las capturas. La entrega excluye bases privadas, claves, sesiones, cuentas de prueba y entornos.

## Observaciones y validación pendiente

- Técnica: probado en Linux/Python 3.12.14; launcher e instrucciones Windows incluidos, sin afirmar prueba nativa Windows/3.11. No se entrega instalador ejecutable ni ruedas para todas las plataformas.
- Protección local: semilla TOTP y backups cifrados; SQLite no está cifrada integralmente. ACL/cifrado de disco, reloj y resguardo separado de clave deben comprobarse en la laptop. No sustituye auditoría independiente de seguridad.
- Datos: referencia y unidades espaciales requieren validación; no hay topografía suficiente ni aceleración aprobada.
- Geotecnia: candidato experimental sin suficientes etiquetas profesionales. Requiere revisión y evaluación de usabilidad por especialistas.
- Futuro: prueba nativa Windows, empaquetado de dependencias offline, revisión externa de seguridad, topografía con referencia aprobada y validación humana de episodios. Ningún cambio automático de modelos/umbrales.

## Trazabilidad del paquete final

`clean_install/clean_validation.json` identifica el ZIP de ejecución limpia y los hashes de su código. Después se incorporaron documentación y evidencias; el código de aplicación permanece idéntico. El único script de prueba modificado espera al formulario y desplaza la pantalla antes de capturar; se volvió a ejecutar correctamente. `delivery_validation.json` documenta esta diferencia, sin presentar los dos ZIP como byte idénticos.

## Conclusión

El flujo de revisión está implementado, reproducible y funciona localmente. La aceptación técnica está respaldada por pruebas y ejecución limpia; las observaciones de plataforma y validación profesional deben cerrarse en el equipo de destino antes de uso institucional.

> GeoSlope Review es una herramienta experimental de apoyo. Las anomalías y episodios mostrados no representan predicciones de falla ni niveles de riesgo. Los resultados requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para tomar decisiones operativas o de seguridad.
