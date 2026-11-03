from gsreview.configuration import COLORS

"""Vistas sin SQL: cada operación utiliza servicios de aplicación autorizados."""
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from gsreview.domain.rules import (
    STATUSES,
    RELEVANCE,
    FOLLOW_UP,
    ReviewInput,
    NOTICE,
    ValidationError,
)
from gsreview.presentation.charts import series

NAV = (
    "Inicio",
    "Bandeja de revisión",
    "Vista espacial",
    "Prismas",
    "Calidad de datos",
    "Reportes",
    "Usuarios",
    "Auditoría",
    "Copias de seguridad",
    "Mi perfil",
)


def login(c):
    left, middle, right = st.columns([1, 1.8, 1])
    with middle:
        st.image(str(c.app_root / "assets/logo.svg"), width=240)
        st.title(c.brand["name"])
        st.caption(c.brand["subtitle"])
        st.markdown('<span class="gs-badge">Sistema local offline</span>', unsafe_allow_html=True)
        if c.store.user_count() == 0:
            st.subheader("Crear administrador")
            st.write("Configura tu cuenta y registra el segundo factor para empezar.")
            with st.form("bootstrap"):
                username = st.text_input("Usuario", key="setup_username")
                name = st.text_input("Nombre visible", key="setup_name")
                password = st.text_input("Contraseña", type="password", key="setup_password")
                repeat = st.text_input("Repetir contraseña", type="password", key="setup_repeat")
                st.caption(
                    "12 caracteres como mínimo; mayúscula, minúscula, número y símbolo; sin tu usuario."
                )
                if st.form_submit_button("Crear administrador", type="primary"):
                    if password != repeat:
                        raise ValidationError("Las contraseñas no coinciden.")
                    st.session_state.challenge = c.auth.bootstrap(username, name, password)
                    st.session_state.auth_stage = "enroll"
                    st.rerun()
        elif "challenge" not in st.session_state:
            st.subheader("Iniciar sesión")
            with st.form("login"):
                username = st.text_input("Usuario", key="login_username")
                password = st.text_input("Contraseña", type="password", key="login_password")
                if st.form_submit_button("Iniciar sesión", type="primary"):
                    challenge, stage = c.auth.password_step(username, password)
                    st.session_state.challenge, st.session_state.auth_stage = challenge, stage
                    st.rerun()
        if "challenge" in st.session_state:
            enroll = st.session_state.auth_stage == "enroll"
            st.subheader("Configurar segundo factor" if enroll else "Verificar identidad")
            if enroll:
                qr, secret = c.auth.enrollment(st.session_state.challenge)
                st.write(
                    "Escanea el QR con tu autenticador. La verificación funciona sin internet."
                )
                st.image(qr, width=210)
                with st.expander("Configuración manual"):
                    st.code(secret)
            recovery = False if enroll else st.checkbox("Usar código de recuperación")
            with st.form("totp"):
                code = st.text_input(
                    "Código de recuperación" if recovery else "Código de seis dígitos",
                    key="otp_code",
                    type="password" if recovery else "default",
                )
                st.caption(
                    "La verificación expira en cinco minutos. Cada código TOTP se acepta una sola vez."
                )
                if st.form_submit_button("Verificar", type="primary"):
                    token, codes = c.auth.second_step(
                        st.session_state.challenge, code.strip(), enroll, recovery
                    )
                    st.session_state.token = token
                    st.session_state.recovery_once = codes
                    del st.session_state.challenge
                    st.rerun()
            if st.button("Volver"):
                st.session_state.pop("challenge", None)
                st.rerun()
        st.caption(
            "Acceso autorizado. Las anomalías requieren revisión geotécnica y no constituyen predicciones de falla."
        )


def dashboard(c, token):
    c.auth.authorize(token)
    st.title("Panorama de revisión")
    st.caption("West Wall · mediciones históricas · política híbrida provisional")
    metrics = c.reader.metrics()
    columns = st.columns(3)
    for i, (label, value) in enumerate(metrics.items()):
        columns[i % 3].metric(label.capitalize(), f"{value:,}")
    st.info("Las anomalías requieren revisión geotécnica y no constituyen predicciones de falla.")
    if st.button("Revisar candidatos pendientes", type="primary"):
        st.session_state.current_page = "Bandeja de revisión"
        st.rerun()
    rows, episodes = c.reader.rows, c.reviews.listing(token)
    a, b = st.columns([1.4, 1])
    with a:
        daily = (
            rows.loc[rows.candidate_hybrid.fillna(False)]
            .groupby(rows.timestamp.dt.date)
            .size()
            .rename("Candidatos")
            .reset_index()
        )
        st.plotly_chart(
            px.bar(
                daily,
                x="timestamp",
                y="Candidatos",
                color_discrete_sequence=[COLORS["teal"]],
                title="Candidatos observados por fecha",
            ),
            width="stretch",
        )
    with b:
        counts = (
            episodes.human_status.value_counts().rename_axis("Estado").reset_index(name="Episodios")
        )
        st.plotly_chart(
            px.bar(
                counts,
                x="Estado",
                y="Episodios",
                color_discrete_sequence=[COLORS["purple"]],
                title="Revisión humana",
            ),
            width="stretch",
        )
    counts = (
        episodes.groupby("prism_id")
        .size()
        .sort_values(ascending=False)
        .rename("Episodios")
        .reset_index()
    )
    st.plotly_chart(
        px.bar(
            counts,
            x="prism_id",
            y="Episodios",
            color_discrete_sequence=[COLORS["blue"]],
            title="Episodios por prisma",
        ),
        width="stretch",
    )
    st.caption(
        f"Evaluables: {int(rows.model_eligible.sum()):,} · No evaluables: {int((~rows.model_eligible).sum()):,} · Última medición: {rows.timestamp.max()} · Integridad comprobada al cargar."
    )


def episode_detail(c, token, episode_id):
    c.auth.authorize(token)
    episode = c.reader.episodes.loc[c.reader.episodes.episode_id.eq(episode_id)].iloc[0]
    st.subheader(f"Episodio · {episode.prism_id}")
    st.caption(episode_id)
    cols = st.columns(4)
    for col, label, value in zip(
        cols,
        ("Marcas", "Coincidencias", "Duración observada (h)", "No evaluables"),
        (
            episode.union_mark_count,
            episode.agreement_count,
            round(episode.duration_hours, 2),
            episode.ineligible_record_count,
        ),
    ):
        col.metric(label, value)
    st.write(episode.episode_explanation)
    with st.expander("Resumen retrospectivo y trazabilidad"):
        st.json(json.loads(episode.to_json(date_format="iso")))
    rows = c.reader.prism_series(episode.prism_id)
    st.plotly_chart(series(rows, episode), width="stretch")
    st.caption(
        "Los máximos y la duración final son retrospectivos. Base q99=4.4398; IF q99=0.5873. Scores en escalas distintas."
    )
    with st.expander("Información causal por registro"):
        selected = c.reader.rows.loc[c.reader.rows.episode_id.eq(episode_id)]
        st.dataframe(
            selected[
                [
                    "timestamp",
                    "model_eligible",
                    "model_ineligibility_reason",
                    "baseline_score",
                    "isolation_forest_score",
                    "union_marks_last_72h",
                    "causal_state",
                    "model_available_at_observation",
                    "candidate_reason",
                ]
            ],
            hide_index=True,
        )
    current = c.reviews.get(token, episode_id)
    st.subheader("Evaluación del especialista")
    with st.form("review_form"):
        a, b = st.columns(2)
        status = a.selectbox(
            "Estado de revisión", STATUSES, index=STATUSES.index(current.get("status", "Pendiente"))
        )
        relevance = b.selectbox(
            "Relevancia profesional",
            RELEVANCE,
            index=RELEVANCE.index(current.get("relevance", "Indeterminado")),
        )
        comment = st.text_area("Comentario técnico", value=current.get("comment", ""))
        quality = st.text_area("Comentario de calidad", value=current.get("quality_comment", ""))
        follow = st.selectbox(
            "Seguimiento recomendado",
            FOLLOW_UP,
            index=FOLLOW_UP.index(current.get("follow_up", FOLLOW_UP[0])),
        )
        if st.form_submit_button("Guardar evaluación", type="primary"):
            c.reviews.save(
                token,
                episode_id,
                ReviewInput(
                    status=status,
                    relevance=relevance,
                    comment=comment,
                    quality_comment=quality,
                    follow_up=follow,
                    expected_version=current["version"],
                ),
            )
            st.success("Evaluación guardada con historial y auditoría.")
    with st.expander("Historial de evaluaciones"):
        history = c.reviews.history(token, episode_id)
        count = len(history)
        versions = "versión guardada" if count == 1 else "versiones guardadas"
        st.caption(f"Episodio {episode_id} · {count} {versions}")
        if history:
            st.dataframe(pd.DataFrame(history), hide_index=True)
        else:
            st.info("Este episodio todavía no tiene evaluaciones guardadas.")


def _restore_review_selection(key, options):
    """Restore module context from a non-widget key after Streamlit widget cleanup."""
    saved = st.session_state.get("review_saved_" + key)
    if key not in st.session_state and saved in options:
        st.session_state[key] = saved
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state.pop(key)


def inbox(c, token):
    c.auth.authorize(token)
    st.title("Bandeja de revisión")
    episodes = c.reviews.listing(token)
    a, b, d = st.columns(3)
    prism_options = ["Todos"] + sorted(episodes.prism_id.unique())
    _restore_review_selection("inbox_prism", prism_options)
    prism = a.selectbox("Prisma", prism_options, key="inbox_prism")
    st.session_state.review_saved_inbox_prism = prism
    status = b.selectbox("Estado", ["Todos"] + list(STATUSES))
    query = d.text_input("Buscar identificador")
    with st.expander("Filtros de evidencia y periodo"):
        dates = st.date_input(
            "Periodo",
            value=(
                episodes.start_timestamp.min().date(),
                episodes.last_observed_timestamp.max().date(),
            ),
        )
        agreement = st.checkbox("Con coincidencia")
        persistence = st.checkbox("Con persistencia")
        quality = st.checkbox("Con interrupción por calidad")
        policy = st.selectbox("Política", ["Todas", "hybrid", "union", "consensus", "persistence"])
        reviewer = st.selectbox(
            "Revisor", ["Todos"] + sorted(x for x in episodes.reviewer_id.unique() if x)
        )
    filtered = episodes.copy()
    if prism != "Todos":
        filtered = filtered.loc[filtered.prism_id.eq(prism)]
    if status != "Todos":
        filtered = filtered.loc[filtered.human_status.eq(status)]
    if query:
        filtered = filtered.loc[filtered.episode_id.str.contains(query, regex=False)]
    if agreement:
        filtered = filtered.loc[filtered.agreement_count.gt(0)]
    if persistence:
        filtered = filtered.loc[filtered.union_mark_count.ge(2)]
    if quality:
        filtered = filtered.loc[filtered.quality_interruption_flag]
    if policy != "Todas":
        filtered = filtered.loc[filtered.candidate_policies.str.contains(policy, regex=False)]
    if reviewer != "Todos":
        filtered = filtered.loc[filtered.reviewer_id.eq(reviewer)]
    if isinstance(dates, tuple) and len(dates) == 2:
        filtered = filtered.loc[
            filtered.start_timestamp.le(pd.Timestamp(dates[1]) + pd.Timedelta(days=1))
            & filtered.last_observed_timestamp.ge(pd.Timestamp(dates[0]))
        ]
    tabs = st.tabs(
        [
            "Candidatos híbridos",
            "Todos los episodios",
            "Marcas no seleccionadas",
            "Interrupciones de calidad",
            "Pendientes",
            "Revisados",
        ]
    )
    selections = [
        filtered.loc[filtered.candidate_policies.str.contains("hybrid")],
        filtered,
        c.reader.rows.loc[
            c.reader.rows.union_mark.fillna(False) & ~c.reader.rows.candidate_hybrid.fillna(False)
        ],
        filtered.loc[filtered.quality_interruption_flag],
        filtered.loc[filtered.human_status.eq("Pendiente")],
        filtered.loc[filtered.human_status.eq("Revisado")],
    ]
    for i, (tab, frame) in enumerate(zip(tabs, selections)):
        with tab:
            st.caption(f"{len(frame)} " + ("marcas conservadas" if i == 2 else "episodios"))
            cols = (
                ["episode_id", "prism_id", "timestamp", "candidate_reason"]
                if i == 2
                else [
                    "episode_id",
                    "prism_id",
                    "start_timestamp",
                    "last_observed_timestamp",
                    "union_mark_count",
                    "agreement_count",
                    "quality_interruption_flag",
                    "human_status",
                    "candidate_policies",
                ]
            )
            limit = c.settings.display_rows(token)
            total_pages = max(1, (len(frame) + limit - 1) // limit)
            key = f"inbox_page_{i}"
            if st.session_state.get(key, 1) > total_pages:
                st.session_state[key] = 1
            number = st.number_input(
                "Página de tabla", min_value=1, max_value=total_pages, value=1, key=key
            )
            st.dataframe(
                frame.iloc[(number - 1) * limit : number * limit][cols],
                hide_index=True,
                width="stretch",
            )
    episode_options = filtered.episode_id.tolist()
    _restore_review_selection("inbox_open_episode", episode_options)
    if filtered.empty:
        st.info("No hay episodios para los filtros seleccionados.")
    else:
        selected = st.selectbox(
            "Abrir episodio",
            episode_options,
            key="inbox_open_episode",
            format_func=lambda x: (
                f"{filtered.loc[filtered.episode_id.eq(x), 'prism_id'].iloc[0]} · {x}"
            ),
        )
        st.session_state.review_saved_inbox_open_episode = selected
        episode_detail(c, token, selected)


def spatial_view(c, token):
    from gsreview.presentation.spatial_workspace import render_workspace

    render_workspace(c, token)


def prisms(c, token):
    c.auth.authorize(token)
    st.title("Detalle del prisma")
    chosen = st.selectbox("Prisma", sorted(c.reader.rows.prism_id.unique()), key="detail_prism")
    rows = c.reader.prism_series(chosen)
    a, b, d = st.columns(3)
    a.metric("Mediciones", len(rows))
    b.metric("Evaluables", int(rows.model_eligible.sum()))
    d.metric("No evaluables", int((~rows.model_eligible).sum()))
    if chosen == "30-1994":
        st.info(
            "Este prisma aparece únicamente en entrenamiento. Sus 15 registros evaluables fueron marcados por ambos métodos. Esto no demuestra una falla y requiere revisión de escala, calidad y contexto geotécnico."
        )
    st.caption(
        f"Periodo: {rows.timestamp.min()} a {rows.timestamp.max()} | Coordenadas de la última observación; unidad original."
    )
    st.dataframe(rows.tail(1)[["easting", "northing", "rl"]], hide_index=True)
    st.plotly_chart(series(rows), width="stretch")
    st.plotly_chart(
        px.line(
            rows,
            x="timestamp",
            y="movement_rate_mm_per_day",
            title="Tasa derivada de movimiento (mm/día) · mediciones irregulares",
        ),
        width="stretch",
    )
    st.caption(
        "Aceleración: no disponible como característica congelada; no se inventa ni se incorpora al modelo."
    )
    st.dataframe(
        rows[
            [
                "timestamp",
                "elapsed_hours",
                "model_eligible",
                "model_ineligibility_reason",
                "causal_state",
                "candidate_reason",
            ]
        ],
        hide_index=True,
    )
    st.dataframe(c.reviews.listing(token).query("prism_id == @chosen"), hide_index=True)


def quality_view(c, token):
    c.auth.authorize(token)
    st.title("Calidad y cobertura")
    rows = c.reader.rows
    bad = rows.loc[~rows.model_eligible]
    st.metric("Registros no evaluables", len(bad))
    st.info(
        "Ausencia de datos no significa estabilidad. La calidad se conserva separada de las marcas estadísticas."
    )
    counts = (
        bad.model_ineligibility_reason.value_counts()
        .rename_axis("Motivo")
        .reset_index(name="Registros")
    )
    st.dataframe(counts, hide_index=True)
    counts = bad.groupby("prism_id").size().rename("Registros").reset_index()
    st.plotly_chart(
        px.bar(
            counts,
            x="prism_id",
            y="Registros",
            color_discrete_sequence=[COLORS["gray"]],
            title="No evaluables por prisma",
        ),
        width="stretch",
    )
    counts = bad.groupby(bad.timestamp.dt.date).size().rename("Registros").reset_index()
    st.plotly_chart(
        px.bar(
            counts,
            x="timestamp",
            y="Registros",
            color_discrete_sequence=[COLORS["gray"]],
            title="No evaluables por fecha",
        ),
        width="stretch",
    )
    st.dataframe(
        bad[
            [
                "prism_id",
                "timestamp",
                "model_ineligibility_reason",
                "hours_since_previous_observation",
            ]
        ],
        hide_index=True,
    )
    st.subheader("Episodios con interrupciones")
    e = c.reviews.listing(token)
    st.dataframe(e.loc[e.quality_interruption_flag], hide_index=True)
    st.subheader("Disponibilidad del modelo")
    st.write(
        "El modelo está disponible desde la frontera de validación: 15 de enero de 2014. Los estados de entrenamiento organizan resultados retrospectivos; no simulan operación en esas fechas."
    )
    st.dataframe(
        rows.groupby(["period", "model_available_at_observation"], dropna=False)
        .size()
        .rename("Registros")
        .reset_index(),
        hide_index=True,
    )


def report_view(c, token):
    c.auth.authorize(token, "export")
    st.title("Reportes y trazabilidad")
    scope = st.selectbox("Tipo de reporte", ["general", "episodio", "prisma"])
    object_id = ""
    if scope == "episodio":
        object_id = st.selectbox("Episodio", c.reader.episodes.episode_id.tolist())
    if scope == "prisma":
        object_id = st.selectbox("Prisma", sorted(c.reader.rows.prism_id.unique()))
    fmt = st.radio("Formato", ["PDF", "CSV", "JSON"], horizontal=True)
    signature = (scope, object_id, fmt)
    if st.button("Generar reporte", type="primary"):
        st.session_state.export_ready = (signature, c.reports.generate(token, *signature))
    prepared = st.session_state.get("export_ready")
    if prepared and prepared[0] == signature:
        mime = {"PDF": "application/pdf", "CSV": "text/csv", "JSON": "application/json"}[fmt]
        st.download_button(
            "Descargar reporte", prepared[1], file_name=f"GeoSlope_{scope}.{fmt.lower()}", mime=mime
        )
    st.info(NOTICE)


def users_view(c, token):
    c.auth.authorize(token, "users")
    st.title("Usuarios y permisos")
    accounts = c.auth.safe_users(token)
    st.dataframe(pd.DataFrame(accounts), hide_index=True)
    with st.expander("Crear usuario"):
        with st.form("new_user"):
            username = st.text_input("Nuevo usuario")
            name = st.text_input("Nombre visible")
            role = st.selectbox("Rol", ["ingeniero", "administrador"])
            password = st.text_input("Contraseña temporal", type="password")
            st.caption(
                "Se exige TOTP y cambio de contraseña al primer acceso. Comunica la contraseña por un canal local autorizado."
            )
            if st.form_submit_button("Crear usuario"):
                c.auth.create_user(token, username, name, password, role)
                st.success("Usuario creado. Debe configurar TOTP al iniciar sesión.")
    target = st.selectbox("Cuenta", accounts, format_func=lambda u: u["username"])
    action = st.selectbox(
        "Acción", ["unlock", "force_change", "reset_totp", "revoke_sessions", "active", "role"]
    )
    value = None
    if action == "active":
        value = st.checkbox("Cuenta activa", value=target["active"])
    if action == "role":
        value = st.selectbox("Nuevo rol", ["ingeniero", "administrador"])
    confirm = st.checkbox("Confirmo la acción sobre la cuenta seleccionada")
    if st.button("Aplicar acción", disabled=not confirm):
        c.auth.user_action(token, target["id"], action, value)
        st.success(
            "Acción registrada. Las sesiones afectadas fueron invalidadas cuando corresponde."
        )
    st.subheader("Sesiones y verificaciones vigentes")
    st.dataframe(pd.DataFrame(c.auth.safe_sessions(token)), hide_index=True)
    st.subheader("Integridad y configuración de presentación")
    if st.button("Verificar artefactos congelados"):
        st.success(f"{c.reviews.verify_integrity(token)} artefactos íntegros.")
    with st.form("display_settings"):
        preference = st.selectbox("Filas por página de la bandeja", [20, 50, 100])
        if st.form_submit_button("Guardar preferencia"):
            c.settings.save(token, "display_rows", str(preference))
            st.success("Preferencia guardada. Los parámetros analíticos permanecen congelados.")


def audit_view(c, token):
    st.title("Auditoría")
    data = pd.DataFrame(c.reviews.audit(token))
    if data.empty:
        st.info("No hay eventos registrados.")
    else:
        action = st.selectbox("Evento", ["Todos"] + sorted(data.action.unique()))
        if action != "Todos":
            data = data.loc[data.action.eq(action)]
        data["fecha_utc"] = pd.to_datetime(data.timestamp, unit="s", utc=True)
        st.dataframe(
            data[["fecha_utc", "actor", "action", "object_id", "detail"]],
            hide_index=True,
            width="stretch",
        )
    st.caption(
        "Registro de solo lectura. Protegido por triggers; un administrador del sistema operativo conserva control sobre los archivos locales."
    )


def backups_view(c, token):
    c.auth.authorize(token, "backup")
    st.title("Copias de seguridad cifradas")
    st.write(
        "Las copias requieren la misma clave local. Guarda una copia de la clave por separado, en un medio protegido."
    )
    if st.button("Crear copia de seguridad", type="primary"):
        c.backups.create(token)
        st.success("Copia cifrada creada y registrada.")
    copies = c.backups.list(token)
    if copies:
        selected = st.selectbox("Copia disponible", copies, format_func=lambda p: p.name)
        st.download_button(
            "Descargar copia cifrada", selected.read_bytes(), file_name=selected.name
        )
    uploaded = st.file_uploader("Copia a restaurar", type=["gsbackup"])
    confirmed = st.checkbox(
        "Confirmo reemplazar los datos de aplicación y cerrar todas las sesiones"
    )
    if st.button("Restaurar copia", disabled=not uploaded or not confirmed):
        c.backups.restore(token, uploaded.getvalue())
        st.session_state.clear()
        st.rerun()


def profile(c, token):
    actor = c.auth.authorize(token, "profile")
    st.title("Mi perfil")
    st.write(f"{actor['display_name']} · {actor['username']} · {actor['role']}")
    if actor["force_change"]:
        st.info("Cambia la contraseña temporal para continuar.")
    with st.form("change_password"):
        old = st.text_input("Contraseña actual", type="password")
        new = st.text_input("Nueva contraseña", type="password")
        repeat = st.text_input("Confirmar nueva contraseña", type="password")
        if st.form_submit_button("Cambiar contraseña"):
            if new != repeat:
                raise ValidationError("Las contraseñas no coinciden.")
            c.auth.change_password(token, old, new)
            st.session_state.clear()
            st.rerun()
    if not actor["force_change"]:
        with st.form("recover_codes"):
            password = st.text_input("Confirmar contraseña", type="password")
            otp = st.text_input("Código TOTP vigente")
            if st.form_submit_button("Regenerar códigos de recuperación"):
                st.session_state.recovery_once = c.auth.regenerate_recovery(token, password, otp)
                st.rerun()
        st.subheader("Mi historial de revisión")
        st.dataframe(pd.DataFrame(c.reviews.history(token)), hide_index=True)


VIEWS = dict(
    zip(
        NAV,
        (
            dashboard,
            inbox,
            spatial_view,
            prisms,
            quality_view,
            report_view,
            users_view,
            audit_view,
            backups_view,
            profile,
        ),
    )
)
