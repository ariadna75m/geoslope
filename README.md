# GeoSlope Review 0.7.5

Aplicación local offline para revisar anomalías estadísticas de prismas y registrar evaluaciones humanas. Monolito modular con Streamlit, servicios Python, SQLAlchemy y SQLite. Usa los artefactos aprobados de Fases 1–6 ubicados en la carpeta superior; no reentrena modelos ni recalcula resultados.

## Inicio en Windows

Descomprime todo el ZIP y conserva la estructura `monitoreo-taludes/geoslope_review`. Abre una terminal dentro de `geoslope_review`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\verify_installation.py
python scripts\initialize_database.py
python scripts\run_app.py
```

También puedes ejecutar `scripts/run_app.bat` después de instalar. La aplicación escucha únicamente en `127.0.0.1:8501`. El asistente crea el primer administrador y exige TOTP. No se distribuyen cuentas, contraseñas, claves, sesiones ni códigos de recuperación. Crea el ingeniero desde Usuarios; al primer acceso configura TOTP y cambia la contraseña temporal.

## Pantallas

Inicio; bandeja y detalle de episodios; vista espacial 2D/3D; prismas; calidad; reportes; usuarios; auditoría; copias de seguridad; perfil. El ingeniero dispone de las siete pantallas correspondientes a su rol. Las funciones administrativas se verifican también en servicios, no solo en navegación.

## Resultados conservados

7.178 filas, 49 prismas, 5.898 evaluables, 1.280 no evaluables, 48 episodios, 102 registros candidatos en 20 episodios. Las 34 marcas no seleccionadas y los cuatro episodios con interrupciones siguen accesibles. La política híbrida usa 72 horas y mínimo dos marcas; sus parámetros y umbrales permanecen congelados.

## Navegación compartida 0.7.3

El sidebar permanece compacto (88 px) en todas las pantallas. Inicio → Revisión → Vista espacial → Prismas → Datos → Reportes → Usuarios → Auditoría. La opción activa tiene fondo azul y una línea cyan; los iconos SVG son locales. El menú de usuario inferior abre Mi perfil y, con permiso, Copias de seguridad. Salir cierra la sesión. Los permisos se consultan en el servicio de autorización existente.

Ver [validación del sidebar](reports/phase7/shared_sidebar.md) y las capturas de ambos roles en `reports/phase7/shared_sidebar/`. La entrega registra 281 pruebas aprobadas.

## Vista espacial conservada de 0.7.2

Menú compacto, filtros horizontales, escena central de mayor tamaño y ficha a la derecha. La selección comienza vacía. Elige un prisma mediante clic 2D/3D o el selector; su ficha y minigráfico se sincronizan. `Centrar` acerca la cámara, `Vista completa` restablece el encuadre, `Ver historial` abre ese prisma y `Revisar episodio` abre el episodio relacionado. Puedes ocultar la ficha desde el menú de usuario. Cámara y filtros trabajan localmente; el renderer Plotly se distribuye en el paquete, sin CDN ni nuevas dependencias Python.

Coordenadas de prismas originales sin unidades/CRS aprobados; no se infiere terreno a partir de ellas. Ver `reports/phase7/compact_redesign.md` para evidencia y limitaciones. Los informes y capturas de versiones anteriores se conservan como antecedentes.

## Relieve integrado 0.7.4

En Vista espacial, activa **Mostrar relieve de Century Mine** para cambiar a la superficie real de Copernicus GLO-30. Usa Vista 2D/3D, la cámara, Vista completa y la exageración vertical 1×/3×/5×. Las cotas conservan sus valores y puedes descargar el GeoTIFF desde Fuente y archivo de relieve. Apaga el control para volver a los prismas y su ficha.

El relieve se distribuye localmente, con resolución aproximada de 30 m. Es una superficie satelital con cotas EGM2008, no un levantamiento detallado del talud ni una captura exacta de 2014. Los filtros instrumentales no cambian esta superficie. La superposición de prismas requiere validar su CRS local, unidades, datum vertical y puntos de control; no se aplicó un desplazamiento arbitrario. No se añaden dependencias geoespaciales a la instalación. Fuente, máscaras de calidad y licencia documentadas en `assets/terrain/`.

## Datos y privacidad local

En 0.7.5, Revisión conserva el prisma y el episodio seleccionado al cambiar de módulo.
El historial indica el identificador del episodio y sus versiones guardadas. Las evaluaciones
siguen almacenadas en SQLite; no se modifica el esquema ni se reinicializan los datos privados.

La base y la clave se crean en `data/runtime/`, excluida del paquete entregado. Configura `GEOSLOPE_RUNTIME` y `GEOSLOPE_KEY_FILE` si deseas otro directorio privado. En Windows restringe el directorio a tu cuenta mediante permisos NTFS. Conserva una copia segura de la clave fuera de la laptop; sin ella no se recuperan TOTP ni backups cifrados.

La instalación descarga dependencias; la ejecución posterior no necesita internet. TOTP requiere un reloj correcto, pero no un proveedor externo. Streamlit usa HTTP/WebSocket **locales** para comunicar navegador y aplicación; el requisito offline se verifica como ausencia de conexiones externas.

## Documentación y validación

- [Instalación](docs/manual_instalacion.md)
- [Usuario](docs/manual_usuario.md)
- [Administrador](docs/manual_administrador.md)
- [Arquitectura](docs/arquitectura.md)
- [Seguridad](docs/seguridad.md)
- [Diccionario](docs/diccionario_datos.md)
- [Limitaciones](docs/limitaciones.md)
- [Validación de Fase 7](reports/phase7/validation_report.md)

Pruebas desde la raíz `monitoreo-taludes`: `PYTHONPATH=geoslope_review python -m pytest -q tests geoslope_review/tests`. En Windows usa `$env:PYTHONPATH="geoslope_review"` antes del comando. Ruff se ejecuta desde la subcarpeta de aplicación: `python -m ruff check .`. Las pruebas de navegador son opcionales para desarrolladores; requieren `requirements-dev.txt` y Chromium local: `python scripts/validate_browser.py --chromium RUTA`.

> GeoSlope Review es una herramienta experimental de apoyo. Las anomalías y episodios mostrados no representan predicciones de falla ni niveles de riesgo. Los resultados requieren revisión de un especialista geotécnico y no deben utilizarse por sí solos para tomar decisiones operativas o de seguridad.
