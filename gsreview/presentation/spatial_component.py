"""Static local Plotly component for actual click selection in both 2D and 3D."""

from pathlib import Path
import streamlit.components.v1 as components

_PATH = Path(__file__).resolve().parents[2] / "assets/spatial_component"
_component = components.declare_component("geoslope_spatial_scene", path=str(_PATH))


def render_scene(figure, revision, key="spatial_scene"):
    return _component(figure=figure.to_json(), revision=revision, key=key, default=None)
