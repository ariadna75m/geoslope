"""Figuras descriptivas: score, calidad y sensibilidad; sin semáforos ni alertas."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from .visualizations import save_pair,BLUE,CYAN,GRAY,GOLD
from .temporal_split import PERIODS

NOTE='Clasificación experimental sin etiquetas reales. Score no es probabilidad, alerta operativa ni riesgo geomecánico.'


def phase5_plots(result,data,tables,output):
    scores=result.scores;assets=[];colors=[BLUE,CYAN,GRAY]
    eligible=scores.loc[scores.model_eligible]
    for model,title in [('baseline','Regla estadística'),('isolation_forest','Isolation Forest')]:
        column=model+'_score';fig,ax=plt.subplots(figsize=(13,7));p=go.Figure()
        for period,color in zip(PERIODS,colors):
            g=eligible.loc[eligible.period.eq(period)]
            displayed=np.log1p(g[column]) if model=='baseline' else g[column]
            ax.hist(displayed,bins=35,alpha=.45,label=period,color=color,density=True)
            p.add_trace(go.Histogram(x=displayed,name=period,opacity=.5,histnorm='probability density',marker_color=color))
        label='log1p(score), solo visualización' if model=='baseline' else 'Score continuo (mayor = más atípico)'
        ax.set_xlabel(label);ax.set_ylabel('Densidad');ax.legend();p.update_layout(barmode='overlay');p.update_xaxes(title=label)
        assets.append(save_pair(fig,p,model+'_distribution',output,title+': distribución por periodo',caption=NOTE))
        fig,ax=plt.subplots(figsize=(14,7));p=go.Figure()
        for period,color in zip(PERIODS,colors):
            g=eligible.loc[eligible.period.eq(period)].sort_values('timestamp')
            displayed=np.log1p(g[column]) if model=='baseline' else g[column]
            ax.scatter(g.timestamp,displayed,s=4,color=color,alpha=.5,label=period)
            p.add_trace(go.Scatter(x=g.timestamp,y=displayed,mode='markers',name=period,marker={'size':3,'color':color},
                                  customdata=g[[column,'prism_id']],hovertemplate='%{x}<br>Score original=%{customdata[0]}<br>Prisma=%{customdata[1]}<extra></extra>'))
        ax.set_ylabel(label);ax.legend();p.update_yaxes(title=label)
        assets.append(save_pair(fig,p,model+'_time',output,title+': scores reales en el tiempo',caption='Cada punto es una medición elegible; no un evento independiente. '+NOTE))
    top=tables['top_scored_observations.csv'].head(20)
    labels=(top.prism_id+' / '+top.timestamp.dt.strftime('%d-%m %H:%M')).tolist()
    fig,ax=plt.subplots(figsize=(14,10));ax.barh(labels[::-1],top.isolation_forest_score.tolist()[::-1],color=BLUE);ax.set_xlabel('Score continuo')
    p=go.Figure(go.Bar(x=top.isolation_forest_score,y=labels,orientation='h',marker_color=BLUE));p.update_yaxes(automargin=True)
    assets.append(save_pair(fig,p,'top_observations',output,'Principales observaciones puntuadas por Isolation Forest',caption=NOTE,height=1100))
    daily=tables['review_workload.csv'].query("group_type=='day'")
    fig,ax=plt.subplots(figsize=(14,7));p=go.Figure()
    for model,color,label in [('baseline',CYAN,'Regla estadística'),('isolation_forest',BLUE,'Isolation Forest')]:
        g=daily.loc[daily.model.eq(model)].sort_values('group_key');days=pd.to_datetime(g.group_key)
        ax.plot(days,g.marked_pct_of_eligible,label=label,color=color)
        p.add_trace(go.Scatter(x=days,y=g.marked_pct_of_eligible,name=label,line_color=color,connectgaps=False))
        unavailable=g.eligible_rows.eq(0)
        if model=='isolation_forest':
            ax.scatter(days.loc[unavailable],np.zeros(unavailable.sum()),marker='x',color=GRAY,label='Sin filas elegibles')
            p.add_trace(go.Scatter(x=days.loc[unavailable],y=np.zeros(unavailable.sum()),mode='markers',name='Sin filas elegibles',marker={'color':GRAY,'symbol':'x'}))
    ax.set_ylabel('% marcado entre elegibles');ax.legend();p.update_yaxes(title='% marcado entre elegibles')
    assets.append(save_pair(fig,p,'daily_marking',output,'Marcación experimental diaria: umbral q99 de entrenamiento',caption='Cruces grises: sin datos elegibles, no normalidad. '+NOTE))
    prism=tables['review_workload.csv'].query("group_type=='prism'").groupby(['model','group_key'],sort=True)[['eligible_rows','marked_rows']].sum().reset_index()
    prism['pct']=100*prism.marked_rows/prism.eligible_rows.replace(0,np.nan)
    fig,ax=plt.subplots(figsize=(14,10));p=go.Figure()
    ids=sorted(scores.prism_id.unique());y=np.arange(len(ids))
    for model,color,shift in [('baseline',CYAN,-.2),('isolation_forest',BLUE,.2)]:
        g=prism.loc[prism.model.eq(model)].set_index('group_key').reindex(ids)
        ax.barh(y+shift,g.pct,height=.4,color=color,label=model)
        p.add_trace(go.Bar(x=g.pct,y=ids,name=model,orientation='h',marker_color=color))
    ax.set_yticks(y,ids);ax.set_xlabel('% marcado entre elegibles');ax.legend();p.update_layout(barmode='group');p.update_yaxes(automargin=True)
    assets.append(save_pair(fig,p,'prism_marking',output,'Marcación experimental por prisma; periodos combinados',caption='Prismas sin elegibilidad permanecen desconocidos. '+NOTE,height=1700))
    seeds=tables['seed_stability.csv'].query('top_fraction==0.02')
    fig,axes=plt.subplots(2,1,figsize=(13,9));p=make_subplots(rows=2,cols=1,subplot_titles=['Correlación de rankings','Jaccard del 2% superior'])
    for period,color in zip(PERIODS,colors):
        g=seeds.loc[seeds.period.eq(period)].sort_values('seed')
        for row,column in enumerate(['ranking_spearman_vs_primary','jaccard_top_vs_primary']):
            axes[row].plot(g.seed.astype(str),g[column],'-o',label=period,color=color)
            p.add_trace(go.Scatter(x=g.seed.astype(str),y=g[column],name=period,line_color=color,showlegend=row==0),row=row+1,col=1)
    axes[0].set_ylabel('Spearman');axes[1].set_ylabel('Jaccard');axes[0].legend();axes[1].set_xlabel('Semilla predefinida')
    assets.append(save_pair(fig,p,'seed_stability',output,'Estabilidad entre semillas: ninguna se elige por conveniencia',caption=NOTE,height=950))
    contamination=tables['contamination_sensitivity.csv'];fig,axes=plt.subplots(2,1,figsize=(13,9));p=make_subplots(rows=2,cols=1,subplot_titles=['Umbral interno','q99 aprendido del entrenamiento'])
    for period,color in zip(PERIODS,colors):
        g=contamination.loc[contamination.period.eq(period)]
        for row,column in enumerate(['marked_internal_pct','marked_q99_pct']):
            axes[row].plot(g.variant,g[column],'-o',color=color,label=period)
            p.add_trace(go.Scatter(x=g.variant,y=g[column],name=period,line_color=color,showlegend=row==0),row=row+1,col=1)
    for ax in axes:ax.set_ylabel('% marcado entre elegibles')
    axes[0].legend();axes[1].set_xlabel('Contaminación configurada')
    assets.append(save_pair(fig,p,'contamination_sensitivity',output,'Sensibilidad a contaminación; score continuo separado del umbral',caption=NOTE,height=950))
    budgets=tables['max_features_sensitivity.csv'].query('top_fraction==0.02')
    fig,axes=plt.subplots(2,1,figsize=(13,9));p=make_subplots(rows=2,cols=1,subplot_titles=['Spearman frente al principal 1.0 (float)','% marcado con q99 de cada entrenamiento'])
    for period,color in zip(PERIODS,colors):
        g=budgets.loc[budgets.period.eq(period)]
        for row,column in enumerate(['ranking_spearman_vs_primary','marked_q99_pct']):
            axes[row].plot(g.variant,g[column],'-o',color=color,label=period)
            p.add_trace(go.Scatter(x=g.variant,y=g[column],name=period,line_color=color,showlegend=row==0),row=row+1,col=1)
    axes[0].set_ylabel('Spearman');axes[1].set_ylabel('% marcado entre elegibles');axes[0].legend()
    assets.append(save_pair(fig,p,'max_features_sensitivity',output,'max_features: entero 1 frente a fracciones 0.5 y 1.0',caption='Variables disponibles por árbol: 1, 8 y 17. Mismo entrenamiento y preprocesamiento congelado. '+NOTE,height=950))
    agreement=tables['model_agreement.csv'];fig,ax=plt.subplots(figsize=(13,7));p=go.Figure()
    for period,color in zip(PERIODS,colors):
        g=agreement.loc[agreement.period.eq(period)]
        ax.plot(100*g.top_fraction,g.jaccard_top,'-o',color=color,label=period)
        p.add_trace(go.Scatter(x=100*g.top_fraction,y=g.jaccard_top,name=period,line_color=color))
    ax.set_xlabel('% superior comparado');ax.set_ylabel('Jaccard entre métodos');ax.legend()
    assets.append(save_pair(fig,p,'method_agreement',output,'Acuerdo de rankings entre regla estadística e Isolation Forest',caption='Desacuerdo no equivale a error. '+NOTE))
    synthetic=tables['synthetic_anomaly_results.csv'];fig,ax=plt.subplots(figsize=(15,11));p=go.Figure()
    names=synthetic.scenario.drop_duplicates().tolist();y=np.arange(len(names))
    for model,color,shift in [('baseline',CYAN,-.2),('isolation_forest',GOLD,.2)]:
        g=synthetic.loc[synthetic.model.eq(model)].set_index('scenario').reindex(names)
        ax.barh(y+shift,100*g.synthetic_marked_fraction,height=.4,label=model,color=color)
        p.add_trace(go.Bar(x=100*g.synthetic_marked_fraction,y=names,name=model,orientation='h',marker_color=color))
    ax.set_yticks(y,names);ax.set_xlabel('% de objetivos sintéticos marcados');ax.legend();p.update_layout(barmode='group');p.update_yaxes(automargin=True)
    assets.append(save_pair(fig,p,'synthetic_sensitivity',output,'Solo pruebas sintéticas: siete alteraciones y dos intensidades',caption='Copias de validación; no eventos geotécnicos ni validación de predicción de fallas.',height=1350))
    comparison=tables['max_features_synthetic_results.csv'];fig,ax=plt.subplots(figsize=(15,11));p=go.Figure()
    names=comparison.scenario.drop_duplicates().tolist();y=np.arange(len(names))
    for label,color,shift in [('1 (int)',GRAY,-.25),('0.5 (float)',CYAN,0),('1.0 (float)',GOLD,.25)]:
        g=comparison.loc[comparison.variant.eq(label)].set_index('scenario').reindex(names)
        ax.barh(y+shift,100*g.synthetic_marked_fraction,height=.25,label=label,color=color)
        p.add_trace(go.Bar(x=100*g.synthetic_marked_fraction,y=names,name=label,orientation='h',marker_color=color))
    ax.set_yticks(y,names);ax.set_xlabel('% de objetivos sintéticos marcados');ax.legend();p.update_layout(barmode='group');p.update_yaxes(automargin=True)
    assets.append(save_pair(fig,p,'max_features_synthetic_comparison',output,'Solo sintéticos: comparación de presupuestos de variables',caption='Mismos 14 escenarios; cada bosque y su umbral de entrenamiento permanecen congelados.',height=1350))
    contribution=tables['feature_descriptive_deviations.csv']
    fig,ax=plt.subplots(figsize=(16,10));ax.barh(contribution.feature_name[::-1],contribution.mean_absolute_training_scaled_deviation[::-1],color=GRAY);ax.set_xlabel('Desviación absoluta escalada con entrenamiento')
    p=go.Figure(go.Bar(x=contribution.mean_absolute_training_scaled_deviation,y=contribution.feature_name,orientation='h',marker_color=GRAY));p.update_yaxes(automargin=True)
    assets.append(save_pair(fig,p,'descriptive_feature_deviations',output,'Desviaciones aproximadas en las 20 observaciones con mayor score',caption='No es importancia causal ni contribución exacta de Isolation Forest. Se usa centro/IQR de entrenamiento.',height=1300))
    train_counts=result.training.groupby('prism_id').size().sort_values(ascending=False)
    new=sorted(set(data.loc[result.periods.eq('validación'),'prism_id'])-set(result.training.prism_id))
    selected=list(dict.fromkeys([*train_counts.head(3).index.tolist(),*new[:2],'30-1994']))
    for prism in selected:
        g=data.loc[data.prism_id.eq(prism)];s=scores.loc[g.index]
        fig,axes=plt.subplots(3,1,figsize=(14,11),sharex=True);p=make_subplots(rows=3,cols=1,shared_xaxes=True,subplot_titles=['Movimiento real reportado','Score continuo Isolation Forest','Regla estadística: log1p solo visual'])
        axes[0].plot(g.timestamp,g.reported_3d_movement_mm,color=BLUE,label='Real reportado');axes[0].set_ylabel('Movimiento (mm)')
        p.add_trace(go.Scatter(x=g.timestamp,y=g.reported_3d_movement_mm,name='Real reportado',line_color=BLUE),row=1,col=1)
        bad=~s.model_eligible
        axes[0].scatter(g.loc[bad,'timestamp'],g.loc[bad,'reported_3d_movement_mm'],color=GRAY,marker='x',s=15,label='No elegible');axes[0].legend(fontsize=8)
        p.add_trace(go.Scatter(x=g.loc[bad,'timestamp'],y=g.loc[bad,'reported_3d_movement_mm'],mode='markers',name='No elegible',marker={'color':GRAY,'symbol':'x'}),row=1,col=1)
        axes[1].plot(g.timestamp,s.isolation_forest_score,color=CYAN);axes[1].set_ylabel('Score IF')
        p.add_trace(go.Scatter(x=g.timestamp,y=s.isolation_forest_score,name='Score IF',line_color=CYAN,connectgaps=False),row=2,col=1)
        axes[2].plot(g.timestamp,np.log1p(s.baseline_score),color=GOLD);axes[2].set_ylabel('log1p(score regla)')
        p.add_trace(go.Scatter(x=g.timestamp,y=np.log1p(s.baseline_score),name='Regla (log1p)',line_color=GOLD,connectgaps=False,customdata=s[['baseline_score']],hovertemplate='Score original=%{customdata[0]}<extra></extra>'),row=3,col=1)
        selection_note='Revisión específica solicitada; no se elimina el prisma ni sus extremos. ' if prism=='30-1994' else 'Selección por conteo de entrenamiento o aparición posterior; sin usar la fecha de falla. '
        assets.append(save_pair(fig,p,'model_prism_'+prism.replace('-','_'),output,'Datos reales y scores: prisma '+prism,caption=selection_note+NOTE,height=1200))
    return assets
