"""Reglas independientes de la interfaz y la base de datos."""

import re
from enum import Enum
from pydantic import BaseModel, Field

NOTICE = (
    "Este reporte presenta anomalías estadísticas y candidatos para revisión. "
    "No constituye una predicción de falla, una clasificación de riesgo ni una "
    "autorización para tomar decisiones operativas."
)
TOPOGRAPHY_NOTICE = (
    "No se dispone de información topográfica suficiente para reconstruir "
    "la superficie del talud. Se presentan únicamente las ubicaciones "
    "instrumentales disponibles."
)


class AccessDenied(Exception):
    pass


class ValidationError(Exception):
    pass


class Role(str, Enum):
    ADMIN = "administrador"
    ENGINEER = "ingeniero"


PERMISSIONS = {
    Role.ADMIN.value: {
        "read",
        "review",
        "export",
        "users",
        "audit",
        "backup",
        "integrity",
        "settings",
        "profile",
    },
    Role.ENGINEER.value: {"read", "review", "export", "profile"},
}
STATUSES = ("Pendiente", "Revisado", "Requiere más información")
RELEVANCE = ("Indeterminado", "Relevante", "No relevante")
FOLLOW_UP = (
    "Verificar datos",
    "Revisar instrumentación",
    "Comparar con inspección de campo",
    "Solicitar mediciones adicionales",
    "Mantener observación",
    "Escalar a evaluación geotécnica",
)


def password_policy(username, password):
    if (
        len(password) < 12
        or len(password) > 256
        or username.lower() in password.lower()
        or not all(
            re.search(pattern, password) for pattern in (r"[A-Z]", r"[a-z]", r"\d", r"[^\w\s]")
        )
    ):
        raise ValidationError(
            "Utiliza entre 12 y 256 caracteres, mayúscula, minúscula, número y símbolo; sin tu usuario."
        )


def username_policy(username):
    if not re.fullmatch(r"[a-z0-9_.-]{3,40}", username):
        raise ValidationError(
            "Usuario: 3 a 40 letras minúsculas, números, punto, guion o guion bajo."
        )


class ReviewInput(BaseModel):
    status: str
    relevance: str
    comment: str = Field(default="", max_length=6000)
    quality_comment: str = Field(default="", max_length=6000)
    follow_up: str
    expected_version: int = Field(ge=0)

    def validate_choices(self):
        if (
            self.status not in STATUSES
            or self.relevance not in RELEVANCE
            or self.follow_up not in FOLLOW_UP
        ):
            raise ValidationError("Valor de revisión no admitido.")
        if self.status == "Revisado" and not self.comment.strip():
            raise ValidationError("Una revisión completada necesita comentario técnico.")
