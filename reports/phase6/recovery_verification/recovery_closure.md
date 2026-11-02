## Verificación de recuperación en esta conversación

Se recuperó el paquete existente Monitoreo_Taludes_Fase6.zip y se comprobó nuevamente, sin repetir las Fases 1–5 ni reentrenar modelos de producción.

- Suite anterior: **158 aprobadas** en 22,09 s, sin fallos ni omisiones.
- Suite completa: **200 aprobadas** en 34,80 s, sin fallos ni omisiones; **42 pruebas nuevas**.
- 426 archivos anteriores intactos; hashes y predicciones de los modelos idénticos.
- Reproducción exacta byte a byte de los 12 CSV; conservación exacta de columnas y tipos al recargar.
- Comprobación de todas las columnas causales en cuatro prefijos de 732, 3.917, 5.453 y 6.799 registros.
- Entrenamiento bloqueado durante la verificación; 10 pares PNG/HTML comprobados.
- 7.178 registros, 49 prismas, 5.898 evaluables y 1.280 no evaluables conservados.

**Observaciones:** la agrupación es causal condicionada a las marcas congeladas; los scores y estados de entrenamiento son retrospectivos. Persistencia e híbrida exigen una marca en el registro actual, decisión conservadora documentada para evitar generar candidatos en filas sin marca. La híbrida conserva 102 candidatos en 20 episodios y 17 prismas, frente a 136 marcas de unión; las 34 marcas excluidas y los cuatro episodios con interrupciones por calidad permanecen accesibles. La ventana de 72 horas y el mínimo de dos marcas requieren validación especializada.

Evidencia actual: `reports/phase6/recovery_verification/previous_tests.txt`, `previous_tests.xml`, `all_tests.txt`, `all_tests.xml`, `reproduction.txt` y `verification_summary.json`.

**Estado: aprobada con observaciones para el alcance técnico experimental.** Los candidatos no son predicciones de falla, no representan niveles de riesgo, requieren revisión de un especialista geotécnico y no deben usarse por sí solos para decisiones operativas o de seguridad.
