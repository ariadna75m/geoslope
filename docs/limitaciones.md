# Limitaciones y decisiones conservadoras

## Datos y geotecnia

Solo un conjunto histórico sin suficientes etiquetas profesionales; no se mide rendimiento sobre fallas reales. El evento del 23-feb-2014 está fuera del periodo y no configura la app. Las marcas/candidatos no son niveles de riesgo ni probabilidades. Ventana 72 h y persistencia 2 requieren validación especializada. Las 34 marcas excluidas y cuatro episodios con interrupciones siguen visibles, aunque no sean seleccionados por híbrida.

Easting, Northing y RL permiten una nube instrumental 3D, pero no tienen unidades, CRS ni datum aprobados. No se inventa terreno, elevación externa, DEM, isolíneas o geometría de mina. No hay comparación fotográfica ni detección de grietas en esta fase: el alcance aprobado utiliza series de prismas. La aceleración no está disponible como variable congelada y la pantalla lo informa.

Los estados de entrenamiento son retrospectivos. La agrupación de Fase 6 es causal condicionada a marcas congeladas; no representa operación en línea en cada fecha de entrenamiento. La falta de datos no demuestra estabilidad. No se unen lluvia, sismicidad o voladuras con relojes y semánticas sin validar.

## Aplicación y seguridad

Uso local por laptop; no despliegue web ni URL pública. Las revisiones son persistentes y versionadas, pero no equivalen a una gestión corporativa de expedientes. La preferencia de filas cambia la paginación de la bandeja, sin limitar el acceso al resto ni cambiar exportaciones o analítica. Se rechaza todo dataset incompatible; no existe carga libre de nuevos modelos.

La DB no está cifrada integralmente; cifrado de disco y ACL son responsabilidad de instalación. Quien controla el sistema operativo puede alterar archivos. El hash del manifiesto detecta cambios frente a esta entrega; no constituye firma de un tercero. TOTP depende de reloj correcto. La recuperación de instalaciones sin clave/recuperaciones/administradores requiere asistencia técnica autorizada; no existe bypass oculto.

Validación ejecutada en Linux/Python 3.12. Windows y Python 3.11 tienen instrucciones y compatibilidad declarada por dependencias, pero no ejecución nativa comprobada en este entorno. La prueba limpia instala dependencias desde el ZIP; la ejecución y el navegador luego bloquean conexiones externas.

## Mejoras futuras

Validación con especialistas y etiquetas humanas; topografía real con referencia aprobada; interoperabilidad local; instalación empaquetada Windows; revisión independiente de seguridad; migraciones versionadas para nuevas fases; pruebas de usabilidad con personas. Ninguna mejora implica reentrenar automáticamente ni cambiar umbrales sin otra fase aprobada.
