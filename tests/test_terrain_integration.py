import hashlib
import json
from shutil import copytree

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from conftest import engineer
from gsreview.domain.rules import ValidationError
from gsreview.presentation.terrain import load_surface, terrain_figure


def test_surface_preserves_values_and_has_its_own_reference(app):
    arrays, metadata = load_surface(app.app_root)
    assert metadata["prism_alignment_validated"] is False
    assert metadata["derived_xyz_horizontal_crs"] == "EPSG:32754"
    assert metadata["vertical_datum"] == "EGM2008, EPSG:3855"
    assert arrays["elevation"].shape == (216, 216)
    assert np.isclose(arrays["elevation"].min(), -147.61557006835938)
    assert np.isclose(arrays["elevation"].max(), 258.1075744628906)
    assert np.diff(arrays["latitude"][:, 0]).max() < 0
    for factor in (1, 3, 5):
        fig = terrain_figure(arrays, "3D", factor)
        assert [t.type for t in fig.data] == ["surface"]
        np.testing.assert_array_equal(fig.data[0].x, arrays["easting"])
        np.testing.assert_array_equal(fig.data[0].y, arrays["northing"])
        np.testing.assert_array_equal(fig.data[0].z, arrays["elevation"])
        assert fig.data[0].customdata is None
    flat = terrain_figure(arrays, "2D")
    assert flat.data[0].type == "heatmap"
    np.testing.assert_array_equal(flat.data[0].z, arrays["elevation"])
    np.testing.assert_array_equal(flat.data[0].x, arrays["longitude"][0])
    np.testing.assert_array_equal(flat.data[0].y, arrays["latitude"][:, 0])
    base, triple = terrain_figure(arrays, "3D", 1), terrain_figure(arrays, "3D", 3)
    assert triple.layout.scene.aspectratio.z == pytest.approx(base.layout.scene.aspectratio.z * 3)


def test_corrupted_or_invalid_surface_is_rejected(app, tmp_path):
    root = tmp_path / "assets/terrain"
    copytree(app.app_root / "assets/terrain", root)
    path = root / "century_surface.npz"
    path.write_bytes(path.read_bytes()[:-5] + b"wrong")
    with pytest.raises(ValidationError, match="versión verificada"):
        load_surface(tmp_path)
    arrays, _ = load_surface(app.app_root)
    arrays["elevation"][0, 0] = np.nan
    np.savez_compressed(path, **arrays)
    meta = json.loads((root / "metadata.json").read_text())
    meta["asset_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / "metadata.json").write_text(json.dumps(meta))
    with pytest.raises(ValidationError, match="datos inválidos"):
        load_surface(tmp_path)


@pytest.mark.parametrize("role", ["administrador", "ingeniero"])
def test_terrain_switch_preserves_prisms_and_works_with_empty_filter(app, monkeypatch, role):
    token = app.test_admin if role == "administrador" else engineer(app)[1]
    monkeypatch.setenv("GEOSLOPE_RUNTIME", str(app.runtime))
    at = AppTest.from_file(str(app.app_root / "app.py"), default_timeout=25)
    at.session_state["token"] = token
    at.session_state["nav"] = "Vista espacial"
    at.run()
    at.selectbox(key="sx_selected").set_value("22-1917").run()
    before = app.reader.rows.copy(deep=True)
    at.toggle(key="sx_terrain").set_value(True).run()
    assert not at.exception and not at.error
    assert any("alineación" in x.value for x in at.info)
    at.selectbox(key="sx_terrain_exaggeration").set_value(5).run()
    assert not at.exception and not at.error
    at.toggle(key="sx_terrain").set_value(False).run()
    assert at.selectbox(key="sx_selected").value == "22-1917"
    at.text_input(key="sx_search").set_value("SIN-PRISMA").run()
    assert any("No existen prismas" in x.value for x in at.info)
    at.toggle(key="sx_terrain").set_value(True).run()
    assert not at.exception and not at.error
    assert any("alineación" in x.value for x in at.info)
    assert app.reader.rows.equals(before)
    assert app.reader.verify() > 10
