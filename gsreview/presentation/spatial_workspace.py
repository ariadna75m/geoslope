"""Compact spatial page: service queries, controller state and two functional panels."""

from datetime import datetime, time
import pandas as pd
import streamlit as st
from gsreview.application.spatial import SpatialService
from gsreview.domain.rules import AccessDenied, ValidationError
from gsreview.presentation.spatial_controller import FILTERS, filter_points, accept_selection
from gsreview.presentation.spatial_component import render_scene
from gsreview.presentation.charts import spatial, movement_preview, STATE_LABELS
from gsreview.presentation.terrain import render_terrain


def _go(page, prism=None, episode=None):
    st.session_state.current_page = page
    st.session_state.nav = page
    if prism is not None:
        st.session_state.detail_prism = prism
    if episode is not None:
        st.session_state.inbox_prism = prism
        st.session_state.inbox_open_episode = episode
    st.rerun(scope="app")


def _refresh():
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    context = get_script_run_ctx()
    st.rerun(scope="fragment" if context and context.fragment_ids_this_run else "app")


def _clear(last_date):
    for key, value in {
        "sx_date": last_date,
        "sx_search": "",
        "sx_state": "Todos",
        "sx_candidates": False,
        "sx_labels": False,
        "sx_dimension": "3D",
        "sx_terrain": False,
    }.items():
        st.session_state[key] = value
    st.session_state.sx_focus = False
    st.session_state.sx_camera_revision = st.session_state.get("sx_camera_revision", 0) + 1


def render_workspace(c, token):
    actor = c.auth.authorize(token, "read")
    c.reader.assert_current()
    service = SpatialService(c)
    if not st.session_state.get("spatial_access_logged"):
        service.log_access(token, "spatial_view_opened")
        st.session_state.spatial_access_logged = True
    css = (c.app_root / "assets/spatial.css").read_text()
    for key, value in c.brand["colors"].items():
        css = css.replace("{{" + key + "}}", value)
    st.html("<style>" + css + "</style>")
    with st.container(key="spatial_workspace"):
        left, right = st.columns([3, 1.4], vertical_alignment="center")
        with left:
            st.title("Vista espacial de prismas")
            st.html(
                '<p class="sx-subtitle">Explora las ubicaciones instrumentales y consulta sus mediciones reales.</p>'
            )
        with right:
            st.html(
                '<div class="sx-status"><span>◉ Offline</span><span>✓ Datos verificados</span></div>'
            )
            with st.popover(
                actor["display_name"], icon=":material/account_circle:", width="stretch"
            ):
                st.caption(actor["role"])
                if st.button("Mi perfil", key="sx_profile"):
                    _go("Mi perfil")
                if st.button("Cerrar sesión", key="sx_logout"):
                    c.auth.logout(token)
                    st.session_state.clear()
                    st.rerun()
                st.toggle("Mostrar ficha", key="sx_detail", value=True)
        _render_body(c, token)


@st.fragment
def _render_body(c, token):
    try:
        _render_content(c, token)
    except AccessDenied:
        st.session_state.clear()
        st.rerun(scope="app")
    except ValidationError as error:
        st.error(str(error))
    except Exception:
        st.error(
            "No se pudo consultar la vista local. Verifica la instalación y la integridad de los datos."
        )


def _render_content(c, token):
    c.auth.authorize(token, "read")
    c.reader.assert_current()
    service = SpatialService(c)
    first, last = c.reader.rows.timestamp.min().date(), c.reader.rows.timestamp.max().date()
    terrain_active = st.session_state.get("sx_terrain", False)
    with st.container(key="spatial_filters"):
        columns = st.columns(
            [1.15, 1.4, 1.4, 1.0, 0.9, 0.95, 0.3], vertical_alignment="bottom", gap="small"
        )
        day = columns[0].date_input(
            "Fecha de corte",
            value=last,
            min_value=first,
            max_value=last,
            key="sx_date",
            disabled=terrain_active,
        )
        search = columns[1].text_input(
            "Buscar prisma",
            placeholder="Identificador…",
            key="sx_search",
            disabled=terrain_active,
        )
        state = columns[2].selectbox(
            "Estado estadístico", list(FILTERS), key="sx_state", disabled=terrain_active
        )
        candidates = columns[3].toggle(
            "Solo candidatos", key="sx_candidates", disabled=terrain_active
        )
        labels = columns[4].toggle("Etiquetas", key="sx_labels", disabled=terrain_active)
        dimension = (
            columns[5].segmented_control(
                "Vista", ["2D", "3D"], default="3D", key="sx_dimension", selection_mode="single"
            )
            or "3D"
        )
        columns[6].button(
            "",
            icon=":material/filter_alt_off:",
            help="Limpiar filtros",
            key="sx_clear",
            on_click=_clear,
            args=(last,),
        )
    if st.toggle(
        "Mostrar relieve de Century Mine",
        key="sx_terrain",
        help="Cambia a la superficie real de la mina. La alineación con los prismas "
        "está pendiente de validar.",
    ):
        if st.session_state.get("sx_selected") is not None:
            st.session_state.sx_saved_selected = st.session_state.sx_selected
        render_terrain(c, dimension)
        return
    st.html(
        '<div class="sx-notice">ⓘ Posiciones instrumentales originales. Activa el relieve '
        "para explorar la superficie de Century Mine.</div>"
    )
    cutoff = pd.Timestamp(datetime.combine(day, time.max))
    points = service.points(token, cutoff)
    visible = filter_points(points, search, state, candidates)
    if visible.empty:
        with st.container(key="spatial_empty"):
            st.info(
                "No existen prismas con los filtros aplicados. Cambia la fecha o pulsa Limpiar filtros."
            )
            st.caption(
                "Selecciona un prisma para consultar sus mediciones. No se añade ninguna posición artificial."
            )
        return
    valid_ids = sorted(visible.prism_id.unique())
    if "sx_selected" not in st.session_state:
        st.session_state.sx_selected = st.session_state.get("sx_saved_selected")
    if st.session_state.get("sx_selected") not in valid_ids:
        st.session_state.sx_selected = None
    pending = st.session_state.pop("sx_pending_selection", None)
    if pending in valid_ids:
        st.session_state.sx_selected = pending
    selected = st.session_state.sx_selected
    show_detail = st.session_state.get("sx_detail", True)
    viewer, panel = st.columns([2.75, 1.0] if show_detail else [100, 0.01], gap="medium")
    with viewer:
        with st.container(key="spatial_scene_panel"):
            plot_title, plot_reset = st.columns([5, 1], vertical_alignment="center")
            plot_title.markdown("**Ubicaciones instrumentales · datos originales**")
            if plot_reset.button(
                "Vista completa", key="sx_reset_camera", help="Restablecer cámara", width="stretch"
            ):
                st.session_state.sx_focus = False
                st.session_state.sx_camera_revision = (
                    st.session_state.get("sx_camera_revision", 0) + 1
                )
                _refresh()
            figure = spatial(
                visible,
                dimension,
                selected=selected,
                focus=st.session_state.get("sx_focus", False),
                labels=labels,
            )
            figure.update_layout(
                title=None,
                height=540,
                margin={"l": 10, "r": 10, "t": 20, "b": 85},
                legend={"orientation": "h", "y": -0.16},
                uirevision=str(st.session_state.get("sx_camera_revision", 0)) + dimension,
            )
            if dimension == "3D" and not st.session_state.get("sx_focus", False):
                figure.update_layout(scene_camera={"eye": {"x": 1.4, "y": 1.4, "z": 1.1}})
            event = render_scene(
                figure, str(st.session_state.get("sx_camera_revision", 0)) + dimension
            )
            selection = accept_selection(event, valid_ids, st.session_state.get("sx_last_nonce"))
            if selection:
                st.session_state.sx_pending_selection, _, st.session_state.sx_last_nonce = selection
                _refresh()
    if show_detail:
        with panel:
            with st.container(key="spatial_detail_panel"):
                chosen = st.selectbox(
                    "Prisma seleccionado",
                    [None] + valid_ids,
                    format_func=lambda value: "Seleccionar prisma…" if value is None else value,
                    key="sx_selected",
                    label_visibility="collapsed",
                    placeholder="Seleccionar prisma…",
                )
                if chosen != selected:
                    _refresh()
                if chosen is None:
                    st.subheader("Selecciona un prisma")
                    st.html(
                        '<p class="sx-subtitle">Selecciona un prisma en la visualización para consultar sus mediciones, episodios y calidad de datos.</p>'
                    )
                else:
                    _render_detail(c, token, service, chosen, visible, cutoff)
    st.caption(
        f"{len(visible)} / {len(points)} posiciones originales al corte · Referencia y unidades pendientes de validación. Visualización instrumental experimental; no representa un mapa de riesgo."
    )


def _render_detail(c, token, service, chosen, visible, cutoff):
    location = visible.loc[visible.prism_id.eq(chosen)].iloc[0]
    rows = service.series(token, chosen, cutoff)
    if rows.empty:
        st.info("Prisma sin mediciones hasta la fecha elegida.")
        return
    latest = rows.iloc[-1]
    title, info = st.columns([5, 1], vertical_alignment="center")
    title.subheader("Prisma " + chosen)
    with info.popover("ⓘ", help="Calidad y disponibilidad del modelo"):
        if chosen == "30-1994":
            st.caption(
                "Este prisma solo figura en entrenamiento. Sus marcas requieren revisión de escala, calidad y contexto geotécnico; no demuestran una falla."
            )
        st.caption(
            str(latest.period)
            + " · Modelo "
            + ("disponible" if latest.model_available_at_observation else "retrospectivo")
        )
        if not location.model_eligible:
            st.caption("Calidad: " + str(latest.model_ineligibility_reason))
        else:
            st.caption("Calidad: " + str(latest.feature_quality_status))
    st.caption(
        STATE_LABELS[location.causal_state]
        + " · "
        + ("Evaluable" if location.model_eligible else "No evaluable")
    )
    table = (
        '<table class="sx-coordinates">'
        + "".join(
            f"<tr><td>{axis}</td><td>{value:.4f}</td></tr>"
            for axis, value in (
                ("Easting", location.easting),
                ("Northing", location.northing),
                ("RL", location.rl),
            )
        )
        + "</table>"
    )
    st.html(table)
    st.caption("Última observación: " + str(location.timestamp))
    ep_ids = rows.loc[rows.episode_id.ne(""), "episode_id"].unique().tolist()
    candidate_rows = rows.loc[rows.candidate_hybrid.fillna(False)]
    a, b = st.columns(2)
    a.metric("Episodios", len(ep_ids))
    b.metric("Candidatos", len(candidate_rows))
    fig = movement_preview(rows)
    fig.update_layout(height=150, margin={"l": 22, "r": 5, "t": 30, "b": 55}, legend={"y": -0.35})
    st.plotly_chart(fig, key="sx_series", width="stretch", theme=None)
    with st.container(key="spatial_actions"):
        first, second = st.columns(2)
        if first.button("Ver historial", key="sx_history", width="stretch"):
            _go("Prismas", chosen)
        if second.button(
            "Centrar", help="Centrar en prisma", key="sx_center", type="primary", width="stretch"
        ):
            st.session_state.sx_focus = True
            st.session_state.sx_camera_revision = st.session_state.get("sx_camera_revision", 0) + 1
            _refresh()
        if ep_ids:
            if st.button("Revisar episodio", key="sx_review", width="stretch"):
                episode_id = ep_ids[-1]
                service.log_access(token, "episode_opened", episode_id)
                _go("Bandeja de revisión", chosen, episode_id)
        else:
            st.caption("No existe un episodio relacionado hasta el corte.")
