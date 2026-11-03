"""Presentation-only filtering and validated click state; never analytical labels."""

import math

FILTERS = {
    "Todos": None,
    "Sin marca": {"sin_marca"},
    "Marca estadística": {"marca_aislada", "episodio_en_observacion"},
    "Candidato para revisión": {"candidato_revision"},
    "No evaluable": {"no_evaluable"},
}


def filter_points(points, search="", state="Todos", only_candidates=False):
    result = points.loc[points.prism_id.str.contains(search.strip(), case=False, regex=False)]
    states = FILTERS.get(state)
    if states is not None:
        result = result.loc[result.causal_state.isin(states)]
    if only_candidates:
        result = result.loc[result.candidate_hybrid.fillna(False)]
    return result


def accept_selection(event, visible_ids, last_nonce):
    if not isinstance(event, dict) or event.get("nonce") == last_nonce:
        return None
    prism = event.get("prism_id")
    if prism not in visible_ids:
        return None
    camera = event.get("camera")
    if camera is not None:
        if not isinstance(camera, dict):
            return None
        for part in ("center", "eye", "up"):
            values = camera.get(part)
            if values is None:
                continue
            if not isinstance(values, dict):
                return None
            if any(
                not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 100
                for v in values.values()
            ):
                return None
    return prism, camera, event.get("nonce")
