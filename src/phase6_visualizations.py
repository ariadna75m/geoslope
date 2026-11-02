"""Descriptive experimental figures, offline HTML and neutral palette."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import get_plotlyjs

COLORS=['#183C60','#65839C','#514D85','#2D7177','#8C939D']


def make_figures(tables, out):
    out=Path(out)
    (out/'figures').mkdir(parents=True,exist_ok=True)
    (out/'interactive').mkdir(parents=True,exist_ok=True)
    (out/'interactive/plotly.min.js').write_text(get_plotlyjs(),encoding='utf-8')
    rows=tables['review_candidates.csv']; episodes=tables['episodes.csv']
    comparison=tables['policy_comparison.csv'].query("period=='total'")
    sensitivity=tables['sensitivity_analysis.csv'].query("period=='total'")
    figures=[]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'})

    def save(number,name,title,ax,interactive):
        fig=ax.figure
        ax.set_title(title+'\nAnomalías estadísticas experimentales',loc='left',fontsize=12,pad=12)
        fig.tight_layout()
        png=f'figures/{number:02d}_{name}.png'; html=f'interactive/{number:02d}_{name}.html'
        fig.savefig(out/png,dpi=160,facecolor='white');plt.close(fig)
        interactive.update_layout(title=title+' — anomalías estadísticas experimentales',template='plotly_white',
                                  colorway=COLORS,font={'family':'Arial','size':13},height=interactive.layout.height or 550,
                                  margin={'l':65,'r':25,'b':100,'t':85})
        interactive.write_html(out/html,include_plotlyjs='plotly.min.js',full_html=True,
                               div_id=f'phase6-{number:02d}-{name}')
        figures.append({'title':title,'png':png,'html':html})

    states=tables['causal_state_counts.csv']
    fig,ax=plt.subplots(figsize=(11,5));ax.barh(states.causal_state,states.rows,color=COLORS);ax.set_xlabel('Registros')
    for n,count in enumerate(states.rows):ax.text(count+35,n,str(count),va='center')
    save(1,'estados','Estados causales por registro',ax,go.Figure(go.Bar(y=states.causal_state,x=states.rows,orientation='h')))
    counts=episodes.groupby('prism_id',sort=True).size().sort_values(kind='stable')
    fig,ax=plt.subplots(figsize=(10,7));ax.barh(counts.index,counts,color=COLORS[0]);ax.set_xlabel('Episodios (ventana de 72 h)')
    save(2,'episodios_prisma','Episodios por prisma',ax,go.Figure(go.Bar(y=counts.index,x=counts,orientation='h')))
    fig,ax=plt.subplots(figsize=(9,5));ax.bar(comparison.policy,comparison.candidate_rows,color=COLORS[:4]);ax.set_ylabel('Registros candidatos')
    for x,n in enumerate(comparison.candidate_rows):ax.text(x,n+1,str(n),ha='center')
    save(3,'politicas','Carga de revisión por política (72 h, mínimo 2)',ax,go.Figure(go.Bar(x=comparison.policy,y=comparison.candidate_rows)))
    daily=tables['daily_candidate_workload.csv']
    fig,ax=plt.subplots(figsize=(12,5));pf=go.Figure()
    for n,(policy,g) in enumerate(daily.groupby('policy',sort=False)):
        ax.plot(g.date,g.candidate_rows,label=policy,color=COLORS[n],linewidth=1.5)
        pf.add_trace(go.Scatter(x=g.date,y=g.candidate_rows,name=policy,mode='lines',line={'color':COLORS[n]}))
    ax.legend(ncol=4);ax.set_ylabel('Registros candidatos por día');fig.autofmt_xdate()
    save(4,'candidatos_dia','Candidatos diarios; ceros no implican estabilidad',ax,pf)
    fig,ax=plt.subplots(figsize=(9,5));ax.hist(episodes.duration_hours,bins=12,color=COLORS[0]);ax.set_xlabel('Horas observadas (resumen retrospectivo)');ax.set_ylabel('Episodios')
    save(5,'duraciones','Duración observada de episodios',ax,go.Figure(go.Histogram(x=episodes.duration_hours,nbinsx=12)))
    fig,ax=plt.subplots(figsize=(9,5));ax.hist(episodes.union_mark_count,bins=np.arange(0.5,max(episodes.union_mark_count.max(),1)+1.5),color=COLORS[2]);ax.set_xlabel('Marcas de unión por episodio');ax.set_ylabel('Episodios')
    save(6,'marcas_episodio','Marcas por episodio; totales retrospectivos',ax,go.Figure(go.Histogram(x=episodes.union_mark_count,xbins={'start':.5,'size':1})))
    b=rows.baseline_mark_q99.fillna(False);f=rows.iforest_mark_q99.fillna(False)
    labels=['Solo modelo base','Coincidencia','Solo Isolation Forest'];values=[int((b&~f).sum()),int((b&f).sum()),int((f&~b).sum())]
    fig,ax=plt.subplots(figsize=(9,5));ax.bar(labels,values,color=COLORS[:3]);ax.set_ylabel('Registros marcados')
    save(7,'coincidencias','Coincidencia entre los métodos',ax,go.Figure(go.Bar(x=labels,y=values)))
    fig,ax=plt.subplots(figsize=(11,5));pf=go.Figure()
    for n,((policy,minimum),g) in enumerate(sensitivity.groupby(['policy','min_marks'],sort=False)):
        g=g.sort_values('window_hours');name=f'{policy}, mínimo {minimum}'
        color=COLORS[list(('union','consensus','persistence','hybrid')).index(policy)]
        ax.plot(g.window_hours,g.candidate_rows,label=name,color=color,linestyle='-' if minimum==2 else '--',marker='o')
        pf.add_trace(go.Scatter(x=g.window_hours,y=g.candidate_rows,name=name,mode='lines+markers',line={'color':color,'dash':'solid' if minimum==2 else 'dash'}))
    ax.set_xticks([24,48,72]);ax.set_xlabel('Ventana temporal (horas)');ax.set_ylabel('Registros candidatos');ax.legend(fontsize=8,ncol=2)
    save(8,'sensibilidad','Sensibilidad temporal de las políticas',ax,pf)
    prism=tables['prism_30_1994_observations.csv']
    fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True);ax=axes[0]
    ax.plot(prism.timestamp,prism.reported_3d_movement_mm,color=COLORS[0],marker='.',label='Movimiento reportado (mm)')
    unknown=~prism.model_eligible;ax.scatter(prism.loc[unknown,'timestamp'],prism.loc[unknown,'reported_3d_movement_mm'],color=COLORS[4],marker='x',label='No evaluable');ax.set_ylabel('Movimiento 3D reportado (mm)');ax.legend();fig.autofmt_xdate()
    pf=make_subplots(rows=3,cols=1,shared_xaxes=True,subplot_titles=('Movimiento reportado (mm)','Score de regla','Score Isolation Forest'))
    pf.add_trace(go.Scatter(x=prism.timestamp,y=prism.reported_3d_movement_mm,name='Movimiento reportado (mm)',mode='lines+markers'),row=1,col=1)
    pf.add_trace(go.Scatter(x=prism.loc[unknown,'timestamp'],y=prism.loc[unknown,'reported_3d_movement_mm'],name='No evaluable',mode='markers',marker={'symbol':'x','color':COLORS[4]}),row=1,col=1)
    for panel,(name,col,threshold) in enumerate([('Base','baseline_score','baseline_threshold_q99'),('Isolation Forest','isolation_forest_score','iforest_threshold_q99')],start=1):
        axes[panel].plot(prism.timestamp,prism[col],color=COLORS[panel],marker='.',label='Score '+name)
        axes[panel].axhline(prism[threshold].iloc[0],color=COLORS[4],linestyle='--',label='q99 congelado')
        axes[panel].set_ylabel('Score '+name);axes[panel].legend(fontsize=9)
        pf.add_trace(go.Scatter(x=prism.timestamp,y=prism[col],name='Score '+name,mode='lines+markers'),row=panel+1,col=1)
        pf.add_hline(y=prism[threshold].iloc[0],line_dash='dash',line_color=COLORS[4],row=panel+1,col=1)
    pf.update_layout(height=850)
    save(9,'prisma_30_1994','Prisma 30-1994; solo entrenamiento, sin diagnóstico',ax,pf)
    selected=episodes.loc[episodes.candidate_policies.str.contains('hybrid',regex=False)].sort_values(['start_timestamp','prism_id']).head(4)
    fig,axes=plt.subplots(len(selected),1,figsize=(12,10),sharex=True);axes=np.atleast_1d(axes);ax=axes[0]
    pf=make_subplots(rows=len(selected),cols=1,subplot_titles=[f'{r.prism_id} / {r.start_timestamp.date()}' for r in selected.itertuples()])
    for n,ep in enumerate(selected.itertuples()):
        g=rows.loc[rows.episode_id.eq(ep.episode_id)]
        x=(g.timestamp-ep.start_timestamp).dt.total_seconds()/3600
        color=COLORS[n];label=f'{ep.prism_id} / {ep.start_timestamp.date()}'
        axes[n].plot(x,g.baseline_score,label=label,color=color,marker='.')
        axes[n].set_ylabel('Score de regla');axes[n].legend(fontsize=9)
        pf.add_trace(go.Scatter(x=g.timestamp,y=g.baseline_score,name=label,mode='lines+markers',line={'color':color}),row=n+1,col=1)
    axes[-1].set_xlabel('Horas desde el inicio del episodio; escalas verticales propias')
    pf.update_layout(height=900)
    save(10,'ejemplos','Primeros cuatro episodios seleccionados cronológicamente',ax,pf)
    return figures
