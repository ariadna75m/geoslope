"""Shared compact navigation. Every destination uses the existing auth service."""

from html import escape
from urllib.parse import quote

import streamlit as st

from gsreview.domain.rules import AccessDenied


# Destination, visible label, required service permission, decorative SVG paths.
ROUTES = (
    ("Inicio", "Inicio", "read", "M3 10l9-7 9 7v11h-6v-7H9v7H3z"),
    (
        "Bandeja de revisión",
        "Revisión",
        "review",
        "M4 4h16v16H4z M7 8h2 M12 8h5 M7 12h2 M12 12h5 M7 16h2 M12 16h5",
    ),
    ("Vista espacial", "Vista espacial", "read", "M12 2l9 5v10l-9 5-9-5V7z M3 7l9 5 9-5 M12 12v10"),
    (
        "Prismas",
        "Prismas",
        "read",
        "M12 2v4 M12 18v4 M2 12h4 M18 12h4 M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0",
    ),
    (
        "Calidad de datos",
        "Datos",
        "read",
        "M20 6c0 2-16 2-16 0s16-2 16 0v12c0 3-16 3-16 0V6 M4 12c0 3 16 3 16 0",
    ),
    ("Reportes", "Reportes", "export", "M5 2h9l5 5v15H5z M14 2v6h5 M8 12h8 M8 16h8"),
    (
        "Usuarios",
        "Usuarios",
        "users",
        "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 22v-3a8 8 0 0 1 16 0v3 M20 4a4 4 0 0 1 0 8",
    ),
    ("Auditoría", "Auditoría", "audit", "M12 2l8 3v7c0 5-8 10-8 10S4 17 4 12V5z M8 12l3 3 5-6"),
)
SECONDARY = (("Mi perfil", "profile"), ("Copias de seguridad", "backup"))


def permitted_pages(c, token):
    """Ask the service, rather than maintaining a separate role permission table."""
    allowed = {}
    for permission in dict.fromkeys([r[2] for r in ROUTES] + [r[1] for r in SECONDARY]):
        try:
            c.auth.authorize(token, permission)
            allowed[permission] = True
        except AccessDenied:
            allowed[permission] = False
    return [r[0] for r in ROUTES if allowed[r[2]]] + [
        page for page, permission in SECONDARY if allowed[permission]
    ]


def navigate(page):
    # nav remains compatible with history/episode links and restored sessions.
    st.session_state.current_page = page
    st.session_state.nav = page


def icon_css(key, path):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'fill="none" stroke="black" stroke-width="1.65" stroke-linecap="round" '
        f'stroke-linejoin="round"><path d="{path}"/></svg>'
    )
    return f'.st-key-{key} button::before{{mask-image:url("data:image/svg+xml,{quote(svg)}");}}'


def render_navigation(c, token, actor):
    choices = permitted_pages(c, token)
    page = st.session_state.get("current_page", st.session_state.get("nav", choices[0]))
    if page not in choices:
        page = choices[0]
    navigate(page)
    css = (c.app_root / "assets/navigation.css").read_text()
    css += "\n" + "\n".join(icon_css("rail_" + str(i), r[3]) for i, r in enumerate(ROUTES))
    css += icon_css("rail_logout", "M9 4H3v16h6 M14 7l5 5-5 5 M7 12h12")
    css += icon_css("rail_profile", "M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 22v-3a8 8 0 0 1 16 0v3")
    st.html("<style>" + css + "</style>")
    with st.sidebar:
        with st.container(key="navigation_rail"):
            st.image(str(c.app_root / "assets/logo_mark.svg"), width=48)
            with st.container(key="rail_links"):
                for i, (destination, label, permission, path) in enumerate(ROUTES):
                    if destination not in choices:
                        continue
                    with st.container(key="rail_" + str(i)):
                        st.button(
                            label,
                            key="rail_" + destination,
                            type="primary" if destination == page else "secondary",
                            width="stretch",
                            on_click=navigate,
                            args=(destination,),
                        )
            with st.container(key="rail_identity"):
                role = "Administrador" if actor["role"] == "administrador" else "Ingeniero"
                with st.container(key="rail_profile"):
                    with st.popover(role, help=actor["display_name"], width="stretch"):
                        st.markdown("**" + escape(actor["display_name"]) + "**")
                        for destination, permission in SECONDARY:
                            if destination in choices:
                                st.button(
                                    destination,
                                    key="rail_" + destination,
                                    on_click=navigate,
                                    args=(destination,),
                                )
                with st.container(key="rail_logout"):
                    if st.button(
                        "Salir", help="Cerrar sesión", key="rail_logout_button", width="stretch"
                    ):
                        c.auth.logout(token)
                        st.session_state.clear()
                        st.rerun()
    return page
