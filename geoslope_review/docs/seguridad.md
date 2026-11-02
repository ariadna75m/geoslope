# Seguridad local

## Controles implementados

Argon2id para contraseñas; política de 12–256 caracteres con mayúscula, minúscula, número y símbolo, sin usuario y sin reutilizar últimas cinco. Sesiones y challenges usan tokens aleatorios de 32 bytes y solo su SHA-256 en SQLite. Challenge de cinco minutos; sesión de 15 minutos de inactividad renovada únicamente en acceso autorizado.

TOTP de seis dígitos, intervalo 30 segundos, tolerancia de un intervalo para reloj. Se conserva el último intervalo aceptado y se rechaza repetición. La semilla se cifra con Fernet. Recuperaciones aleatorias de 80 bits, diez por conjunto, guardadas como SHA-256 y usadas una sola vez. Regenerar exige contraseña y TOTP nuevo. Configurar TOTP no permite acceder a otras páginas antes de verificarlo.

Cinco fallos consecutivos producen bloqueo de 15 minutos; reintentos se espacian progresivamente 1, 2, 4, 8 y hasta 30 segundos. Se usa una referencia Argon2 artificial para usuarios inexistentes y mensaje genérico. La espera se implementa con fecha de próximo intento, no con bloqueos sleep del servidor. Los eventos fallidos y bloqueos se auditan. Cuentas desactivadas no acceden; las acciones de seguridad revocan sesiones.

RBAC en servicios y en navegación. Guards transaccionales repiten autorización antes de mutaciones. El ingeniero no puede crear usuarios, cambiar roles, restaurar backups, leer auditoría global, editar analítica ni obtener semillas de terceros. Los parámetros analíticos solo se leen. Auditoría append-only por triggers; no se exponen modificaciones en UI.

Servidor restringido a loopback, CORS/XSRF habilitados, telemetría deshabilitada. Excepciones inesperadas se muestran sin traza ni secretos. Las funciones administrativas sensibles exigen confirmación en la interfaz. CSV escapa textos que podrían interpretarse como fórmulas. PDF escapa comentarios antes de procesarlos como contenido de ReportLab.

## Protección del equipo

La clave vive fuera del código, en directorio runtime privado, con modo 0600 en Linux; en Windows configura ACL NTFS para la cuenta autorizada. Protege el directorio completo, incluidos WAL/SHM. Los backups se cifran, pero la base SQLite no usa SQLCipher: **comentarios/revisiones locales no están cifrados en reposo dentro de SQLite**. Usa cifrado de disco del equipo y control de acceso del sistema operativo si necesitas esa protección.

La clave junto a la base solo protege contra acceso parcial; quien controla completamente el equipo puede leer o alterar datos y recuperar secretos. No se afirma resistencia a administrador/root, certificación, defensa contra toda amenaza, auditoría criptográficamente inmutable ni autenticación equivalente a infraestructura corporativa. No expongas este servidor a internet sin otra evaluación de seguridad.

## Referencias de implementación

- [API argon2-cffi](https://argon2-cffi.readthedocs.io/en/stable/api.html)
- [PyOTP y prevención de replay](https://pyauth.github.io/pyotp/)
- [Pruebas Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)

Las pruebas propias verifican los controles; no constituyen pentest externo ni certificación.
