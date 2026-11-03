import io
import json
import socket
import pandas as pd
import pytest
from pypdf import PdfReader
from gsreview.domain.rules import ReviewInput, ValidationError, AccessDenied
from gsreview.application.container import Container
from gsreview.analytics.artifacts import FrozenReader
from conftest import engineer


def review(c, token, episode, version=0, comment="Evaluación exclusivamente sintética de prueba."):
    c.reviews.save(
        token,
        episode,
        ReviewInput(
            status="Revisado",
            relevance="Indeterminado",
            comment=comment,
            quality_comment="Comprobar referencia.",
            follow_up="Verificar datos",
            expected_version=version,
        ),
    )


def test_frozen_counts_relationships_and_full_visibility(app):
    r, e = app.reader.rows, app.reader.episodes
    assert len(r) == 7178 and r.prism_id.nunique() == 49 and (~r.model_eligible).sum() == 1280
    assert len(e) == 48 and r.candidate_hybrid.sum() == 102
    assert (r.union_mark.fillna(False) & ~r.candidate_hybrid.fillna(False)).sum() == 34
    assert e.quality_interruption_flag.sum() == 4
    assert e.candidate_policies.str.contains("hybrid").sum() == 20
    assert app.reader.verify() > 10


def test_engineer_review_history_conflict_and_restart(app):
    _, token, _ = engineer(app)
    episode = app.reader.episodes.episode_id.iloc[0]
    review(app, token, episode)
    with pytest.raises(ValidationError):
        review(app, token, episode)
    review(app, token, episode, version=1, comment="Segunda versión sintética.")
    restarted = Container(runtime=app.runtime, clock=app.auth.clock)
    assert restarted.reviews.get(token, episode)["version"] == 2
    assert len(restarted.reviews.history(token, episode)) == 2


@pytest.mark.parametrize("fmt", ["PDF", "CSV", "JSON"])
@pytest.mark.parametrize("scope", ["general", "prisma", "episodio"])
def test_report_formats_scopes_and_human_traceability(app, fmt, scope):
    episode = app.reader.episodes.iloc[0]
    review(app, app.test_admin, episode.episode_id)
    obj = {"general": "", "prisma": episode.prism_id, "episodio": episode.episode_id}[scope]
    content = app.reports.generate(app.test_admin, scope, obj, fmt)
    if fmt == "PDF":
        reader = PdfReader(io.BytesIO(content))
        text = "".join(p.extract_text() for p in reader.pages)
        assert (
            "GeoSlope Review" in text
            and "Evaluación exclusivamente" in text
            and "predicción de falla" in text
        )
    elif fmt == "JSON":
        value = json.loads(content)
        assert value["reviews"] and value["artifacts"] and value["notice"]
    else:
        rows = pd.read_csv(io.BytesIO(content))
        assert rows.report_notice.notna().all() and rows.human_comment.notna().any()


def test_backup_restore_encrypted_sessions_revoked_audit_preserved(app):
    episode = app.reader.episodes.episode_id.iloc[0]
    review(app, app.test_admin, episode)
    path = app.backups.create(app.test_admin)
    assert b"password_hash" not in path.read_bytes()
    review(app, app.test_admin, episode, version=1, comment="Versión que será restaurada.")
    app.backups.restore(app.test_admin, path.read_bytes())
    assert app.store.list("episode_reviews")[0]["version"] == 1
    with pytest.raises(AccessDenied):
        app.auth.authorize(app.test_admin)
    actions = [r["action"] for r in app.store.list("audit_log")]
    assert "review_modified" in actions and "backup_restored" in actions
    assert len(list(app.backups.directory.glob("*.gsbackup"))) == 2


def test_backup_corruption_rejected_transaction_preserved(app):
    path = app.backups.create(app.test_admin)
    bad = path.read_bytes()[:-10] + b"broken"
    with pytest.raises(ValidationError):
        app.backups.restore(app.test_admin, bad)
    assert app.auth.authorize(app.test_admin)


def test_settings_only_non_analytical(app):
    app.settings.save(app.test_admin, "display_rows", "50")
    with pytest.raises(ValidationError):
        app.settings.save(app.test_admin, "window_hours", "24")


def test_spatial_real_coordinates_and_temporal_cutoff(app):
    cutoff = pd.Timestamp("2014-01-01")
    points = app.reader.spatial(cutoff)
    assert points.timestamp.le(cutoff).all() and not points.prism_id.duplicated().any()
    f = app.reader.features.set_index("source_record_id")
    for r in points.itertuples():
        assert (r.easting, r.northing, r.rl) == tuple(
            f.loc[r.source_record_id, ["easting", "northing", "rl"]]
        )
    assert app.reader.spatial("1900-01-01").empty


def test_import_idempotent_and_offline_initialization(app, monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("External network not allowed")

    monkeypatch.setattr(socket.socket, "connect", denied)
    c = Container(runtime=tmp_path / "offline")
    c.reviews.import_initial()
    assert len(c.store.list("episodes")) == 48 and len(c.store.list("data_imports")) == 1


def test_manifest_tampering_rejected(app, tmp_path):
    manifest = dict(app.reader.manifest)
    manifest["files"] = dict(manifest["files"])
    name = next(iter(manifest["files"]))
    manifest["files"][name] = "0" * 64
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(manifest))
    with pytest.raises(ValidationError):
        FrozenReader(app.source, target)


def test_exports_denied_without_authenticated_session(app):
    with pytest.raises(AccessDenied):
        app.reports.generate("invalid", "general", "", "PDF")
