"""Gráficos de validación de Fase 4; reutiliza exportación sin cambiar Fase 3."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .visualizations import save_pair, histogram, bar_plot, BLUE, GOLD, GRAY, CYAN
from .config import WINDOWS
from .temporal_features import local_trend
from .feature_engineering import RATE_DESCRIPTION


def feature_plots(data, quality, groups, selected, config, output):
    assets = []
    for column, name, title, unit in (
        ("elapsed_hours", "interval_distribution", "Intervalos temporales observados", "Horas entre mediciones"),
        ("movement_delta_mm", "change_distribution", "Cambios entre mediciones; signos conservados", "Cambio reportado (mm)"),
        ("movement_rate_mm_per_day", "rate_distribution", RATE_DESCRIPTION, "Tasa observada (mm/día)"),
        ("local_trend_72h_slope_mm_per_day", "trend72_distribution", "Tendencia estadística local: ventana 72 h", "Pendiente local (mm/día)"),
        ("local_trend_7d_slope_mm_per_day", "trend7_distribution", "Tendencia estadística local: ventana 7 días", "Pendiente local (mm/día)")):
        assets.append(histogram(data[column], name, title, output, unit,
                                caption="Distribución de calculables, extremos conservados. Tasa y pendiente no son velocidad física validada ni diagnóstico."))
    assets.append(bar_plot(groups.feature_group, groups.available_pct, "availability_groups", "Disponibilidad matemática por grupo", output,
                           "Porcentaje de filas", horizontal=True,
                           caption="Denominador: todas las filas conservadas. Disponibilidad no equivale a cobertura temporal completa o confianza geomecánica."))
    calculated = quality.loc[~quality.group.isin(["source", "availability"]) & quality.nan_pct.gt(0)]
    highest = calculated.sort_values(["nan_pct", "feature_name"], ascending=[False, True]).head(30)
    assets.append(bar_plot(highest.feature_name, highest.nan_pct, "missing_features", "Treinta características con mayor porcentaje de NaN", output,
                           "Porcentaje de filas", horizontal=True,
                           caption="Todas las columnas y sus porcentajes aparecen en feature_quality_summary.csv. Faltantes no se imputan."))
    for prism in selected:
        g = data[data.prism_id.eq(prism)].sort_values("timestamp")
        fig, axes = plt.subplots(4, 1, figsize=(13, 12), sharex=True)
        p = make_subplots(rows=4, cols=1, shared_xaxes=True,
                          subplot_titles=["Movimiento reportado y ajuste local retrospectivo", RATE_DESCRIPTION,
                                          "Pendientes locales", "Observaciones por ventana"])
        axes[0].plot(g.timestamp, g.reported_3d_movement_mm, "-o", color=BLUE, markersize=1, label="Original reportado")
        p.add_trace(go.Scatter(x=g.timestamp, y=g.reported_3d_movement_mm, name="Original reportado", line_color=BLUE), row=1, col=1)
        eligible = g.loc[g.local_trend_72h_slope_mm_per_day_available]
        if len(eligible):
            last = eligible.iloc[-1].timestamp
            window = g.loc[g.timestamp.gt(last-pd.Timedelta(hours=72)) & g.timestamp.le(last)]
            fit = local_trend(window.timestamp, window.reported_3d_movement_mm, config, 72*config.min_window_span_fraction)
            center_x = (window.timestamp-window.timestamp.iloc[0]).dt.total_seconds()/86400
            fitted = window.reported_3d_movement_mm.mean()+fit["slope_mm_per_day"]*(center_x-center_x.mean())
            axes[0].plot(window.timestamp, fitted, color=GOLD, linestyle="--", label="Ajuste en última ventana 72h calculable")
            p.add_trace(go.Scatter(x=window.timestamp, y=fitted, name="Ajuste retrospectivo 72h", line_color=GOLD, line_dash="dash"), row=1, col=1)
        axes[0].set_ylabel("Movimiento (mm)"); axes[0].legend(fontsize=7)
        axes[1].plot(g.timestamp, g.movement_rate_mm_per_day, color=CYAN); axes[1].set_ylabel("Tasa (mm/día)")
        p.add_trace(go.Scatter(x=g.timestamp, y=g.movement_rate_mm_per_day, name="Tasa observada", line_color=CYAN, connectgaps=False), row=2, col=1)
        for label, color in [("72h", BLUE), ("7d", GOLD)]:
            col = f"local_trend_{label}_slope_mm_per_day"
            axes[2].plot(g.timestamp, g[col], color=color, label=label)
            p.add_trace(go.Scatter(x=g.timestamp, y=g[col], name="Pendiente "+label, line_color=color, connectgaps=False), row=3, col=1)
        axes[2].set_ylabel("Pendiente (mm/día)"); axes[2].legend(fontsize=7)
        for (label, _), color in zip(WINDOWS, [BLUE, GRAY, GOLD]):
            col = f"window_{label}_observation_count"
            axes[3].plot(g.timestamp, g[col], color=color, label=label)
            p.add_trace(go.Scatter(x=g.timestamp, y=g[col], name="Conteo "+label, line_color=color), row=4, col=1)
        axes[3].set_ylabel("Observaciones"); axes[3].legend(fontsize=7)
        assets.append(save_pair(fig, p, "features_prism_"+prism.replace("-", "_"), output,
                                "Validación temporal: prisma "+prism,
                                caption="Ajuste limitado a una ventana pasada, sin extrapolación. NaN deja huecos. Segmentar líneas no genera nuevas mediciones; ninguno de estos valores diagnostica estabilidad.", height=1250))
    return assets
