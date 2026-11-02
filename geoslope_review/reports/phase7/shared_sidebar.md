# Fase 7 — Sidebar compartido y navegación, versión 0.7.3

Se retomó el paquete 0.7.2 existente. Se implementó una única navegación compacta para todos los módulos, conservando la distribución funcional de Vista espacial. No se reconstruyó el proyecto.

## Resultado

- Sidebar permanente de 88 px, fondo azul marino y logo centrado. Iconos lineales SVG locales y texto debajo; sin expansión al pasar el puntero.
- Orden: Inicio → Revisión → Vista espacial → Prismas → Datos → Reportes → Usuarios → Auditoría. Revisión abre la bandeja y Datos abre Calidad y cobertura.
- Opción activa con fondo azul semitransparente, línea cyan en el borde izquierdo e icono/texto cyan. Hover sin desplazamiento y foco visible para teclado.
- Perfil/rol y Salir anclados abajo. Mi perfil y Copias de seguridad están en el menú del usuario; esta última solo aparece con autorización. En alturas reducidas, la navegación se desplaza independientemente.
- Cada destino mantiene `current_page` y `nav` sincronizados. Los accesos a historial, episodios y candidatos conservan su destino; se eliminó la alternancia entre menú compacto y menú ancho.

## Autorización y conservación

Las opciones se obtienen consultando el servicio de autorización existente por permiso, sin otra tabla de roles en la interfaz. Los servicios siguen imponiendo sus propios controles. El ingeniero no ve Usuarios, Auditoría ni Copias de seguridad. Una cuenta con cambio de contraseña pendiente solo puede abrir Mi perfil y salir.

El código de `domain`, `application`, `analytics` e `infrastructure` permanece idéntico. Se conservan Argon2id, TOTP, recuperación, auditoría, esquema SQLite y funcionamiento offline. No se reentrenaron los modelos del proyecto.

La comparación SHA-256 contra el ZIP 0.7.2 confirma **507 archivos de Fases 1–6 sin cambios** y **637 archivos existentes idénticos**. Los **17 artefactos congelados** mantienen su integridad. Evidencia: `sidebar_preservation.json` y `sidebar_integrity.json`.

Se mantienen 7.178 registros, 49 prismas, 48 episodios y 102 registros candidatos en 20 episodios. Vista espacial conserva filtros horizontales, selección 2D/3D, gráfico grande, ficha lateral, minigráfico, historial y centrado. No se cambian coordenadas, unidades, estados, puntajes ni política analítica.

## Validación

La suite conjunta completa aprueba **281 pruebas, cero errores, fallos o pruebas omitidas**: 269 existentes y 12 regresiones nuevas. Estas últimas cubren navegación desde otro módulo, persistencia después de un rerender, restricciones de ingeniero, intento de restaurar una página administrativa, logout y cambio obligatorio de contraseña. Dos pruebas previas se adaptaron al reemplazo del radio por botones; conservan sus comprobaciones funcionales.

```bash
PYTHONPATH=geoslope_review python -m pytest -q tests geoslope_review/tests
cd geoslope_review
python scripts/verify_installation.py
python scripts/validate_browser.py --chromium /ruta/a/chromium --output reports/phase7/shared_sidebar/screenshots
python scripts/validate_sidebar.py --chromium /ruta/a/chromium
```

Evidencia: `sidebar_all_tests.xml`, `sidebar_all_tests.txt` y `sidebar_ruff.txt`. Ruff aprobado. La validación se ejecutó en Linux y Python 3.12.14; no se afirma haber realizado una prueba nativa en Windows.

El recorrido E2E completo con administrador verifica bootstrap/TOTP, navegación, clic real 2D/3D, ficha sincronizada, filtros, centrado, pantalla completa, guardado de revisión, PDF, copia cifrada y logout. Evidencia: `shared_sidebar/browser_validation.json`.

El recorrido E2E de navegación verifica todos los destinos principales para ambos roles, acceso al perfil, copias para administrador, ocultamiento de funciones administrativas para ingeniero, cambio inicial de contraseña, logout de ambos roles, sidebar estable al hacer hover y resolución de poca altura. Inicio, Revisión y Vista espacial se verifican en **1366×768, 1440×900 y 1920×1080** para ambos roles. Se comprueba ancho de 88 px, perfil/logout visibles, ausencia de scroll horizontal y de superposición con el contenido. La escena espacial conserva al menos 60 % del ancho útil. Evidencia: `shared_sidebar/navigation_validation.json`.

Ambos recorridos usan cuentas y base temporales, eliminadas al terminar. No hubo solicitudes externas. Las capturas finales solo contienen cuentas sintéticas y datos del proyecto.

## Capturas

Las capturas de cada rol y resolución están en `shared_sidebar/`. Las de selección 2D/3D, ficha, filtros y el flujo completo están en `shared_sidebar/screenshots/`.

## Archivos modificados

`app.py` delega al nuevo componente `gsreview/presentation/navigation.py`. `assets/navigation.css` concentra el estilo compartido; `assets/spatial.css` conserva los estilos de la escena y elimina sus reglas exclusivas de sidebar. Se añadieron `tests/test_shared_navigation.py` y `scripts/validate_sidebar.py`, y se ajustaron selectores E2E para la navegación compartida. Se actualizó la documentación y la versión a 0.7.3.

La entrega sigue siendo una aplicación local offline. Este cambio no constituye un despliegue web. Las marcas estadísticas y candidatos requieren evaluación geotécnica; el visor no predice fallas ni representa un mapa de riesgo.
