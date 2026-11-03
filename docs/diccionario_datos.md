# Diccionario de datos de aplicación

| Elemento | Fuente o formato | Significado |
|---|---|---|
| source_record_id | Fase 6, string | Identificador original preservado |
| prism_id | Fases 4/6, string | Prisma; nunca mezcla episodios entre prismas |
| timestamp | datetime sin zona validada | Fecha del archivo; no se convierte a UTC ficticiamente |
| easting/northing/rl | Fase 4, float | Posiciones originales; unidades/CRS/datum pendientes |
| reported_3d_movement_mm | Fase 6, float | Movimiento reportado en mm, sin asumir acumulación estricta |
| movement_rate_mm_per_day | Fase 4, float o desconocido | Tasa derivada aprobada, sin reinterpretar como velocidad física validada |
| model_eligible | bool | Elegibilidad original |
| model_ineligibility_reason | string | Motivo exacto del registro no evaluable |
| baseline_score/isolation_forest_score | float o desconocido | Puntuaciones congeladas, escalas diferentes |
| candidate_hybrid | bool nullable | Selección provisional por la política congelada |
| causal_state | string | Estado por registro de Fase 6; no nivel de riesgo |
| model_available_at_observation | bool | Distingue entrenamiento retrospectivo de evaluación posterior al ajuste |
| episode_id | string | ID determinista aprobado |
| start/last_observed_timestamp | datetime | Resumen retrospectivo del episodio |
| human_status | derivado de revisión | Pendiente por ausencia de revisión, o valor ingresado por persona |
| version | integer | Versión de evaluación humana, control de concurrencia |
| reviewer/updated_at | ID y epoch UTC | Persona autenticada y hora de evaluación; no fecha histórica del sensor |

## SQLite

`users`, `roles`, `password_history`, `recovery_codes`, `sessions`, `login_attempts`, `app_metadata`, `data_imports`, `episodes`, `episode_reviews`, `review_history`, `audit_log`, `report_history`, `artifact_integrity`, `backup_history`.

Los campos JSON de episodios conservan el resumen aprobado. `episode_reviews` contiene estado humano actual; `review_history` guarda todas las versiones. `audit_log` tiene identificadores UUID sin FK a usuario para conservar evidencia tras una restauración. Fechas de aplicación son epoch UTC; se muestran como UTC en auditoría. Fechas originales no se sincronizan con sismicidad/lluvia. No hay binarios de modelos en SQLite ni etiquetas automáticas de falla.

El manifiesto JSON contiene rutas relativas y SHA-256 exactos. Los registros fuente mantienen floats mediante lectura round_trip; JSON usa representación nativa sin el redondeo de tablas visuales. CSV conserva todos los registros para el alcance escogido, con datos humanos y advertencia.
