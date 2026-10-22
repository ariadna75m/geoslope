# Corrección del historial de evaluaciones · 0.7.5

Al cambiar de módulo, Streamlit limpiaba los selectores de prisma y episodio.
La evaluación permanecía guardada en SQLite, pero Revisión abría otro episodio
sin evaluaciones. Se conserva la selección en claves independientes de los widgets.
Los enlaces desde Vista espacial pueden abrir un episodio diferente de forma explícita.
El historial ahora muestra el identificador del episodio y la cantidad de versiones.

Validación: 288 pruebas aprobadas, incluida guardar → Reportes → Revisión
con administrador e ingeniero, reapertura de la base y exportación de la evaluación.
Los 507 archivos originales de las Fases 1–6 permanecen intactos y se verifican
los 17 artefactos congelados. No se cambia el esquema ni los permisos.

## Aplicar la actualización en Windows

Detén Streamlit con Ctrl+C y abre PowerShell en la carpeta monitoreo-taludes.
Extrae GeoSlope_075_Correccion_historial.zip en esa misma carpeta con sobrescritura.
El parche contiene solamente código y documentación de geoslope_review.
Conserva data/runtime: contiene los usuarios, la clave y las evaluaciones existentes.
Arranca la aplicación desde la misma carpeta geoslope_review de antes.
Selecciona una vez el prisma y el episodio que ya habías evaluado;
los cambios de módulo conservarán esa selección durante la sesión.
