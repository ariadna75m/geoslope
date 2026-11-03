# Instalación y recuperación

## Requisitos

Python 3.11 o posterior, laptop con navegador moderno, espacio para datos y backups. Validación realizada en Linux con Python 3.12; los comandos y launcher Windows están preparados, pero esta entrega no afirma haber ejecutado Windows ni Python 3.11. Se recomiendan 8 GB de RAM. Conserva completa la carpeta superior con datos/modelos de las fases anteriores.

## Windows

1. Descomprime el ZIP en una carpeta local, fuera de directorios públicos o sincronizados sin autorización.
2. Abre PowerShell en `monitoreo-taludes/geoslope_review`.
3. Ejecuta los comandos del README para crear `.venv`, activar e instalar.
4. Si PowerShell impide activar, usa directamente `.venv\Scripts\python.exe -m pip install -r requirements.txt` y el mismo ejecutable para los scripts.
5. `verify_installation.py` comprueba módulos, firmas SHA-256 y resultados aprobados antes de iniciar.
6. `initialize_database.py` crea esquema, roles e importación; no crea usuarios.
7. `run_app.bat` o `python scripts/run_app.py` inicia el servidor restringido a loopback.
8. Abre `http://127.0.0.1:8501`, crea administrador, escanea QR, valida TOTP y guarda los diez códigos mostrados una vez.
9. Crea el ingeniero y verifica ambos roles. La contraseña temporal se elige durante esa creación; no hay valor predeterminado.

## Linux/macOS

Usa `python -m venv .venv`, `source .venv/bin/activate`, `python -m pip install -r requirements.txt`, `python scripts/initialize_database.py` y `python scripts/run_app.py`.

## Offline y secretos

La instalación inicial puede requerir internet; para instalación totalmente desconectada prepara previamente wheels compatibles con el sistema. No se incluyen ruedas binarias para todas las plataformas. La aplicación, gráficos, QR, TOTP, PDF, SQLite y backups funcionan localmente. Bloquea conexiones externas si el equipo lo exige; permite loopback para Streamlit.

La clave Fernet se genera al primer inicio en `data/runtime/master.key`, nunca en el código. Puede cambiarse la ubicación mediante `GEOSLOPE_KEY_FILE` antes de iniciar. **No borres ni regeneres la clave de una instalación existente**: invalidaría las semillas TOTP cifradas y copias. Protege el archivo con ACL NTFS en Windows; en Linux se crean clave y DB con modo 0600. Protege asimismo el directorio y sus archivos WAL/SHM.

## Errores y continuidad

Dependencia faltante: instala el archivo requirements dentro de `.venv`. Artefacto alterado: no cambies el manifiesto para silenciarlo; recupera el paquete aprobado. Puerto ocupado: cierra otra instancia o usa un puerto local diferente. TOTP rechazado: revisa el reloj y espera un código nuevo; los códigos ya utilizados se rechazan. Cuenta bloqueada: espera 15 minutos o solicita desbloqueo al administrador. Si pierdes TOTP usa un código de recuperación; si pierdes además códigos y todos los administradores, conserva archivos y requiere recuperación técnica autorizada. No existe una cuenta secreta de rescate.

Para recuperar datos utiliza la pantalla de backups y la misma clave local. Antes de restaurar se genera otra copia; todas las sesiones se invalidan. Los eventos de auditoría actuales se conservan y se añaden los de la copia que faltan.
