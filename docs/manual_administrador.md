# Manual del administrador

## Usuarios

Crea cuentas con nombre, usuario, rol y contraseña temporal elegida por ti. Cada persona registra su propio TOTP y cambia contraseña al primer acceso. No envíes semillas ni recuperaciones de otra persona; el sistema no las expone en la administración.

Puedes activar/desactivar, asignar rol, desbloquear, forzar cambio, restablecer TOTP o revocar todas las sesiones de una cuenta. Marca la confirmación antes de aplicar. Desactivar, cambiar rol, forzar cambio, restablecer TOTP y revocar cierran las sesiones correspondientes. El último administrador activo no puede desactivarse ni perder su rol. No existe eliminación de usuarios: sus identificadores permanecen para conservar referencias de revisión.

Restablecer TOTP genera una nueva semilla cifrada y borra recuperaciones previas; al siguiente inicio la persona debe configurar el autenticador. El administrador no ve la nueva semilla. Los intentos y sesiones se muestran sin sus tokens.

## Auditoría e integridad

Auditoría es de solo lectura y registra autenticación, bloqueos, cuentas, revisiones, importación, exportaciones, backups y configuración. Los triggers impiden modificar o borrar eventos por las rutas normales de SQL. Un administrador del sistema operativo puede alterar archivos; protege la laptop y no consideres estos triggers un registro forense certificado.

Verificar artefactos recalcula firmas SHA-256 contra el manifiesto de entrega y registra el resultado. El lector rechaza fuentes alteradas. La importación inicial es idempotente; no se admite reemplazar por otro dataset desde la interfaz porque los resultados y decisiones están congelados. Para un nuevo conjunto se necesita una fase aprobada y migración explícita; no edites hashes para forzar compatibilidad.

La única configuración modificable desde Usuarios es la preferencia no analítica de presentación. Marca, subtítulo, versión y paleta se centralizan en `config/app_config.yaml`; los valores analíticos no son editables.

## Backups

Crea copias `.gsbackup` cifradas con la clave local. No incluyen sesiones. Descarga y conserva fuera del equipo junto con una copia protegida **separada** de la clave. Antes de restaurar se exige confirmación, se verifica esquema/manifiesto y se crea una copia preventiva. La restauración es transaccional, mantiene auditoría actual, recupera revisiones y revoca sesiones. No se restaura una copia sin administrador activo y TOTP configurado.

Los backups no sustituyen la copia del paquete de datos/modelos congelados; estos permanecen fuera de SQLite y se verifican por firma. Los backups contienen hashes de contraseña y TOTP cifrado dentro de un contenedor cifrado: trátalos como información confidencial.
