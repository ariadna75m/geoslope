# Validación de seguridad

## Implementación y comprobaciones

- Argon2id y validación de contraseña: 12 caracteres, mayúscula, minúscula, número, símbolo, exclusión del usuario, historial de cinco. Hash/semilla/datos sensibles no se exponen en DTO de usuarios.
- Mensaje genérico para usuario desconocido o contraseña inválida; cinco fallos consecutivos, bloqueo 15 minutos y espera progresiva. Eventos registrados.
- Contraseña genera desafío de cinco minutos; aún no es sesión autenticada. TOTP de seis dígitos, periodo 30 s, tolerancia de un paso, contador anti-repetición; se comprueba código inválido/válido y repetición.
- Diez recuperaciones aleatorias, solo hashes y uso único; regeneración exige contraseña y TOTP. QR y semilla nunca se incluyen en capturas; se ocultaron antes de guardar.
- Token de sesión aleatorio, solo hash en DB, expiración a 15 minutos de inactividad; logout y cambios sensibles revocan sesiones. Cuenta desactivada sin acceso.
- Roles verificados en cada vista y servicio; ingeniero sin administración, backup/restauración ni secretos. Último administrador activo protegido. Confirmación en interfaz para acciones sensibles.
- Clave Fernet generada localmente, excluida de ZIP, semilla TOTP cifrada y backups cifrados. No hay contraseña o cuenta predeterminada.
- SQLAlchemy parametrizado, transacciones, historial con versión optimista, CSV con protección ante fórmula; acceso de exportaciones requiere sesión y permiso.
- Auditoría registra autenticación, usuarios, revisión, exportación/reportes, integridad, importación y backup/restauración. Triggers rechazan UPDATE/DELETE; eventos no contienen contraseña, tokens o códigos.
- Configuración Streamlit: loopback, XSRF/CORS, telemetría desactivada, trazas internas no presentadas. Sin recursos externos en el recorrido probado.

## Evidencia y límites

58 casos nuevos y ejecución limpia de ambos roles aprobados; consultar XML y reportes de flujo. Los secretos de validación fueron aleatorios en directorios temporales. Las capturas son de usuarios sintéticos; no se distribuyen sus bases, claves ni recuperaciones.

Esto no constituye prueba de penetración independiente. La base SQLite no está cifrada integralmente; requiere ACL y cifrado de disco según instalación. Quien controla el sistema operativo puede cambiar DB/archivos. Un hash no constituye firma de un tercero. Protege la clave separada de backups y conserva reloj correcto. No existe bypass de recuperación oculto.

> GeoSlope Review es una herramienta experimental de apoyo. Las anomalías y episodios mostrados no representan predicciones de falla ni niveles de riesgo. Los resultados requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para tomar decisiones operativas o de seguridad.
