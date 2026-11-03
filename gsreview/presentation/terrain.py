"""Offline, independently georeferenced surface; no inferred prism alignment."""

import hashlib
import io
import json

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from gsreview.configuration import COLORS
from gsreview.domain.rules import ValidationError
from gsreview.presentation.spatial_component import render_scene


def load_surface(app_root):
    root = app_root / "assets/terrain"
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    content = (root / "century_surface.npz").read_bytes()
    if hashlib.sha256(content).hexdigest() != metadata["asset_sha256"]:
        raise ValidationError("El archivo de relieve no coincide con su versión verificada.")
    with np.load(io.BytesIO(content), allow_pickle=False) as stored:
        arrays = {
            name: stored[name]
            for name in ("easting", "northing", "elevation", "longitude", "latitude")
        }
    if any(
        a.shape != tuple(metadata["shape"]) or not np.isfinite(a).all() for a in arrays.values()
    ):
        raise ValidationError("La malla de relieve contiene datos inválidos.")
    return arrays, metadata


def terrain_figure(arrays, dimension="3D", exaggeration=3):
    if dimension not in ("2D", "3D") or exaggeration not in (1, 3, 5):
        raise ValidationError("Vista de relieve no válida.")
    # Keep true UTM and EGM2008 values. Aspect ratio alone exaggerates the relief.
    east, north, z = (arrays[k] for k in ("easting", "northing", "elevation"))
    figure = go.Figure()
    if dimension == "3D":
        figure.add_trace(
            go.Surface(
                x=east.tolist(),
                y=north.tolist(),
                z=z.tolist(),
                colorscale="Earth",
                colorbar={"title": "Cota (m)<br>EGM2008"},
                hovertemplate="Este UTM: %{x:.1f} m<br>Norte UTM: %{y:.1f} m"
                "<br>Cota EGM2008: %{z:.1f} m<extra></extra>",
            )
        )
        span = max(float(np.ptp(east)), float(np.ptp(north)))
        figure.update_layout(
            scene={
                "xaxis_title": "Este UTM 54S (m)",
                "yaxis_title": "Norte UTM 54S (m)",
                "zaxis": {"title": "Cota EGM2008 (m)", "nticks": 4},
                "aspectmode": "manual",
                "aspectratio": {
                    "x": float(np.ptp(east)) / span,
                    "y": float(np.ptp(north)) / span,
                    "z": float(np.ptp(z)) / span * exaggeration,
                },
                "camera": {"eye": {"x": 0.7, "y": -0.9, "z": 0.65}},
                "bgcolor": COLORS["spatial_panel"],
            }
        )
    else:
        # Geographic grid stays exact; 2D does not pretend to be a rectilinear UTM raster.
        longitude, latitude = arrays["longitude"], arrays["latitude"]
        figure.add_trace(
            go.Heatmap(
                x=longitude[0].tolist(),
                y=latitude[:, 0].tolist(),
                z=z.tolist(),
                colorscale="Earth",
                colorbar={"title": "Cota (m)<br>EGM2008"},
                hovertemplate="Longitud: %{x:.6f}°<br>Latitud: %{y:.6f}°"
                "<br>Cota EGM2008: %{z:.1f} m<extra></extra>",
            )
        )
        figure.update_layout(xaxis_title="Longitud WGS84 (°)", yaxis_title="Latitud WGS84 (°)")
        figure.update_yaxes(scaleanchor="x", scaleratio=1 / np.cos(np.deg2rad(-18.73)))
    figure.update_layout(
        height=540,
        margin={"l": 75 if dimension == "2D" else 15, "r": 20, "t": 20, "b": 65},
        paper_bgcolor=COLORS["spatial_panel"],
        plot_bgcolor=COLORS["spatial_panel"],
        font={"color": COLORS["spatial_text"]},
        showlegend=False,
    )
    return figure


def render_terrain(c, dimension):
    arrays, metadata = load_surface(c.app_root)
    st.info(
        "Relieve de Century Mine · resolución aproximada de 30 m. "
        "La alineación con los prismas está pendiente de validar."
    )
    with st.container(key="spatial_terrain_panel"):
        title, scale, reset = st.columns([3, 1.6, 1], vertical_alignment="bottom")
        title.markdown("**Relieve real · Copernicus GLO-30**")
        exaggeration = 1
        if dimension == "3D":
            exaggeration = scale.selectbox(
                "Exageración vertical",
                [1, 3, 5],
                index=1,
                format_func=lambda value: f"{value}×",
                key="sx_terrain_exaggeration",
            )
        if reset.button("Vista completa", key="sx_terrain_reset", width="stretch"):
            st.session_state.sx_terrain_revision = (
                st.session_state.get("sx_terrain_revision", 0) + 1
            )
        revision = (
            f"terrain-{dimension}-{exaggeration}-{st.session_state.get('sx_terrain_revision', 0)}"
        )
        figure = terrain_figure(arrays, dimension, exaggeration)
        figure.update_layout(uirevision=revision)
        render_scene(figure, revision, key="terrain_scene")
    st.caption(
        "Superficie satelital con referencia propia: WGS84 / UTM 54S y cotas EGM2008. "
        "No es un levantamiento detallado del talud ni una captura exacta de 2014. "
        "Los filtros de fecha, estado y prisma corresponden a la vista de prismas."
    )
    with st.expander("Fuente y archivo de relieve"):
        st.caption(metadata["attribution"])
        st.download_button(
            "Descargar GeoTIFF",
            (c.app_root / "assets/terrain/century_copernicus_dsm_30m.tif").read_bytes(),
            file_name="century_copernicus_dsm_30m.tif",
            mime="image/tiff",
            key="sx_terrain_download",
        )
        st.caption(
            "La georreferencia local y el datum vertical de los prismas deben confirmarse "
            "antes de superponerlos sobre esta superficie."
        )
