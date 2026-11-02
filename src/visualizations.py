"""Figuras descriptivas en PNG y Plotly HTML sin modificar los datos recibidos."""
from pathlib import Path
from io import BytesIO
import os
import tempfile
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
from plotly.subplots import make_subplots
from .exploratory_analysis import DISCLAIMER,SOUTH_DESCRIPTION,WEST_DESCRIPTION,ordered_prisms

BLUE='#16324f';GOLD='#b68412';GRAY='#6f7c89';CYAN='#258fa6'
PALETTE=[BLUE,CYAN,GRAY,GOLD,'#526d82','#6ba3b2','#879dab','#766c4c','#30576d','#a7bac5']
FAILURE_LABEL='Fecha de falla documentada en el artículo: 23-02-2014'
BLAST_LABEL='Voladura documentada en hora local; alineación temporal con prismas pendiente de validar'
SPATIAL_NOTE='Las coordenadas, CRS y datum requieren validación. El gráfico representa posiciones relativas del conjunto'


def save_pair(fig,pfig,name,output_dir,title,*,caption='',height=620):
    out=Path(output_dir)
    if name.startswith('south_') and SOUTH_DESCRIPTION not in title:
        title=title+' — '+SOUTH_DESCRIPTION
    if name in {'west_range','west_documentary_dates'} and WEST_DESCRIPTION not in caption:
        caption=caption+' '+WEST_DESCRIPTION
    if 'raw' in out.resolve().parts or 'processed' in out.resolve().parts:raise ValueError('No se escriben gráficos dentro de datos originales/procesados.')
    (out/'figures').mkdir(parents=True,exist_ok=True);(out/'interactive').mkdir(exist_ok=True)
    fig.suptitle('\n'.join(textwrap.wrap(title,80)),fontsize=14,fontweight='bold',color=BLUE,y=.98)
    footer='\n'.join(textwrap.wrap(caption+' '+DISCLAIMER,125))
    fig.text(.065,.018,footer,fontsize=8,color=GRAY,va='bottom')
    tall=fig.get_size_inches()[1]>15
    fig.subplots_adjust(top=.94 if tall else .86,bottom=.08 if tall else .24,left=.13,right=.95)
    for ax in fig.axes:ax.tick_params(labelsize=8);ax.grid(alpha=.18,axis='x')
    # Validar en memoria y sustituir de forma atómica: no publicar un PNG parcial.
    buffer=BytesIO()
    fig.savefig(buffer,format='png',dpi=150,bbox_inches='tight');plt.close(fig)
    payload=buffer.getvalue()
    with Image.open(BytesIO(payload)) as picture:picture.verify()
    target=out/'figures'/f'{name}.png'
    with tempfile.NamedTemporaryFile(dir=target.parent,suffix='.tmp',delete=False) as temporary:
        temporary.write(payload);temporary_name=temporary.name
    os.replace(temporary_name,target)
    pfig.update_layout(title={'text':'<br>'.join(textwrap.wrap(title,85)),'x':.03},template='plotly_white',height=height,colorway=PALETTE,
                       margin={'t':100,'b':160,'l':100,'r':50},font={'family':'Arial','color':BLUE},
                       annotations=[*pfig.layout.annotations,dict(text='<br>'.join(textwrap.wrap(caption+' '+DISCLAIMER,125)),
                         x=0,y=-.22,xref='paper',yref='paper',xanchor='left',showarrow=False,font={'size':10,'color':GRAY})])
    # One shared local JS file: all HTML files remain usable without internet.
    pfig.write_html(out/'interactive'/f'{name}.html',include_plotlyjs='directory',full_html=True,div_id=name)
    return {'name':name,'title':title,'png':f'figures/{name}.png','html':f'interactive/{name}.html','caption':caption}


def bar_plot(x,y,name,title,output_dir,xlabel,*,caption='',horizontal=False,color=BLUE):
    fig,ax=plt.subplots(figsize=(12,max(11,len(x)*.18) if horizontal else 6))
    if horizontal:
        ax.barh(list(x),list(y),color=color);ax.set_xlabel(xlabel);p=go.Figure(go.Bar(x=list(y),y=list(x),orientation='h',marker_color=color))
    else:
        ax.bar(list(x),list(y),color=color);ax.set_ylabel(xlabel);ax.tick_params(axis='x',rotation=90)
        p=go.Figure(go.Bar(x=list(x),y=list(y),marker_color=color))
    return save_pair(fig,p,name,output_dir,title,caption=caption,height=max(1100,len(x)*24+300) if horizontal else 620)


def histogram(values,name,title,output_dir,xlabel,*,caption=''):
    x=pd.to_numeric(values).dropna();fig,ax=plt.subplots(figsize=(12,6));ax.hist(x,bins=40,color=BLUE,alpha=.85)
    ax.set_xlabel(xlabel);ax.set_ylabel('Observaciones medidas')
    p=go.Figure(go.Histogram(x=x,nbinsx=40,marker_color=BLUE));p.update_xaxes(title=xlabel);p.update_yaxes(title='Observaciones medidas')
    return save_pair(fig,p,name,output_dir,title,caption=caption)


def west_plots(data,profiles,selected,availability,output_dir):
    d=ordered_prisms(data);value='reported_3d_movement_mm';unit='Movimiento 3D reportado (mm)';results=[]
    results.append(bar_plot(profiles.prism_id,profiles.observations,'west_observations','West Wall: observaciones por prisma',output_dir,'Número de observaciones',horizontal=True))
    results.append(histogram(d[value],'west_distribution','West Wall: distribución del movimiento reportado',output_dir,unit,caption=WEST_DESCRIPTION))
    fig,ax=plt.subplots(figsize=(12,13));groups=[g[value].dropna().to_numpy() for _,g in d.groupby('prism_id',sort=True)]
    ax.boxplot(groups,orientation='horizontal',tick_labels=profiles.prism_id,showfliers=True);ax.set_xlabel(unit)
    p=go.Figure()
    for prism,g in d.groupby('prism_id',sort=True):p.add_trace(go.Box(x=g[value],name=prism,orientation='h',showlegend=False,boxpoints='outliers'))
    results.append(save_pair(fig,p,'west_boxplot',output_dir,'West Wall: distribución por prisma; valores extremos conservados',caption=WEST_DESCRIPTION,height=1400))
    for row in selected.itertuples():
        g=d[d.prism_id.eq(row.prism_id)];fig,ax=plt.subplots(figsize=(12,6));ax.plot(g.timestamp,g[value],'-o',markersize=2,color=BLUE);ax.set_ylabel(unit)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'));ax.tick_params(axis='x',rotation=25)
        p=go.Figure(go.Scatter(x=g.timestamp,y=g[value],mode='lines+markers',name=row.prism_id,line_color=BLUE))
        p.update_yaxes(title=unit);label='; cobertura insuficiente (<20)' if row.coverage_insufficient else ''
        results.append(save_pair(fig,p,'west_series_'+row.prism_id.replace('-','_'),output_dir,'West Wall: prisma '+row.prism_id+label,
                                 caption='Selección: '+row.selection_groups+'. '+WEST_DESCRIPTION))
    fig,ax=plt.subplots(figsize=(14,12));im=ax.imshow(availability.to_numpy(),aspect='auto',cmap='Blues',interpolation='nearest')
    ax.set_yticks(range(len(availability)),availability.index);ticks=np.linspace(0,len(availability.columns)-1,8,dtype=int)
    ax.set_xticks(ticks,[availability.columns[i].strftime('%d-%m-%Y') for i in ticks],rotation=30);fig.colorbar(im,ax=ax,label='Observaciones por día')
    p=go.Figure(go.Heatmap(z=availability.to_numpy(),x=availability.columns,y=availability.index,colorscale='Blues',colorbar_title='Obs./día'))
    results.append(save_pair(fig,p,'west_availability',output_dir,'West Wall: disponibilidad diaria por prisma',caption='0 indica ausencia de observación en el día, no movimiento cero; no se infiere frecuencia uniforme.',height=1250))
    fig,ax=plt.subplots(figsize=(12,6));ax.scatter(profiles[value+'_initial'],profiles[value+'_final'],color=BLUE)
    ax.set_xlabel('Valor inicial reportado (mm)');ax.set_ylabel('Valor final reportado (mm)')
    p=go.Figure(go.Scatter(x=profiles[value+'_initial'],y=profiles[value+'_final'],text=profiles.prism_id,mode='markers',marker_color=BLUE))
    p.update_xaxes(title='Valor inicial (mm)');p.update_yaxes(title='Valor final (mm)')
    results.append(save_pair(fig,p,'west_initial_final',output_dir,'West Wall: comparación entre primera y última observación',caption='Cada prisma puede tener un período distinto. '+WEST_DESCRIPTION))
    results.append(bar_plot(profiles.prism_id,profiles[value+'_range'],'west_range','West Wall: rango observado por prisma',output_dir,'Máximo − mínimo reportado (mm)',horizontal=True,caption='Rango descriptivo; no clasifica estabilidad.'))
    first=d.drop_duplicates('prism_id',keep='first');fig,ax=plt.subplots(figsize=(12,7));ax.scatter(first.easting,first.northing,color=BLUE);ax.set_aspect('equal',adjustable='datalim')
    ax.set_xlabel('Easting (unidad pendiente)');ax.set_ylabel('Northing (unidad pendiente)')
    p=go.Figure(go.Scatter(x=first.easting,y=first.northing,text=first.prism_id,mode='markers',marker_color=BLUE))
    p.update_xaxes(title='Easting (unidad pendiente)');p.update_yaxes(title='Northing (unidad pendiente)',scaleanchor='x',scaleratio=1)
    results.append(save_pair(fig,p,'west_spatial',output_dir,'West Wall: posiciones relativas de la primera observación por prisma',caption=SPATIAL_NOTE))
    fig,ax=plt.subplots(figsize=(13,7));p=go.Figure()
    for i,(prism,g) in enumerate(d[d.prism_id.isin(selected.prism_id)].groupby('prism_id',sort=True)):
        ax.plot(g.timestamp,g[value],label=prism,linewidth=1,color=PALETTE[i%len(PALETTE)])
        p.add_trace(go.Scatter(x=g.timestamp,y=g[value],mode='lines',name=prism,line_color=PALETTE[i%len(PALETTE)]))
    last=d.timestamp.max();failure=pd.Timestamp('2014-02-23');ax.axvline(last,color=GRAY,linestyle='--',label='Fin de observaciones: 20-02-2014')
    ax.axvline(failure,color=GOLD,linestyle=':',label=FAILURE_LABEL);ax.set_xlim(d.timestamp.min(),failure+pd.Timedelta(days=1));ax.set_ylabel(unit);ax.legend(fontsize=7,ncol=2,loc='upper left')
    p.add_vline(x=last,line_dash='dash',line_color=GRAY);p.add_vline(x=failure,line_dash='dot',line_color=GOLD)
    p.update_xaxes(range=[d.timestamp.min(),failure+pd.Timedelta(days=1)]);p.update_yaxes(title=unit)
    caption=FAILURE_LABEL+'. Fin de datos: 20-02-2014. Referencia solo por fecha, no hora exacta ni reloj sincronizado. '+BLAST_LABEL+'. No se enlaza a mediciones ni se calcula anticipación.'
    results.append(save_pair(fig,p,'west_documentary_dates',output_dir,'West Wall: límite de observaciones y fecha documental de falla',caption=caption,height=800))
    return results


def south_plots(data,profiles,selected,output_dir):
    results=[];cols=['easting_diff','northing_diff','height_diff'];d=ordered_prisms(data)
    results.append(bar_plot(profiles.prism_id,profiles.observations,'south_observations','South West: observaciones por prisma',output_dir,'Observaciones',horizontal=True,caption=SOUTH_DESCRIPTION))
    for c in cols:
        results.append(histogram(d[c],'south_distribution_'+c,'South West: distribución de '+c,output_dir,c+' (unidad pendiente)',caption=SOUTH_DESCRIPTION))
        results.append(bar_plot(profiles.prism_id,profiles[c+'_range'],'south_range_'+c,'South West: rango por prisma de '+c,output_dir,'Rango (unidad pendiente)',horizontal=True,caption=SOUTH_DESCRIPTION))
    for row in selected.itertuples():
        g=d[d.prism_id.eq(row.prism_id)];fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True);p=make_subplots(rows=3,cols=1,shared_xaxes=True,subplot_titles=cols)
        for i,c in enumerate(cols):
            axes[i].plot(g.timestamp,g[c],color=BLUE,marker='o',markersize=1);axes[i].set_ylabel(c+'\n(unidad pendiente)')
            p.add_trace(go.Scatter(x=g.timestamp,y=g[c],mode='lines+markers',name=c),row=i+1,col=1)
        if len(g)==1:
            bounds=[g.timestamp.iloc[0]-pd.Timedelta(hours=12),g.timestamp.iloc[0]+pd.Timedelta(hours=12)]
            axes[-1].set_xlim(*bounds)
            p.update_xaxes(range=bounds)
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
        if len(g)==1:
            axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y %H:%M'))
            axes[-1].tick_params(axis='x',rotation=25)
        results.append(save_pair(fig,p,'south_series_'+row.prism_id.replace('-','_'),output_dir,'South West: prisma '+row.prism_id,
                                 caption=SOUTH_DESCRIPTION+'. Selección: '+row.selection_groups+'. Los segmentos unen mediciones; no se imputan valores en huecos.', height=950))
    return results


def rainfall_plots(data,monthly,output_dir):
    results=[];d=data.sort_values('timestamp');unknown=d[d.rainfall_mm.isna()]
    fig,ax=plt.subplots(figsize=(13,6));ax.plot(d.timestamp,d.rainfall_mm,color=BLUE,linewidth=.7);ax.scatter(unknown.timestamp,np.zeros(len(unknown)),marker='x',color=GOLD,label='Desconocidos (marcador en base; no valor cero)')
    ax.set_ylabel('Lluvia reportada (mm)');ax.legend(fontsize=8)
    p=go.Figure(go.Scatter(x=d.timestamp,y=d.rainfall_mm,mode='lines',name='Lluvia medida',connectgaps=False,line_color=BLUE))
    p.add_trace(go.Scatter(x=unknown.timestamp,y=np.zeros(len(unknown)),mode='markers',name='Desconocidos: marcador, no 0 mm',marker={'symbol':'x','color':GOLD}))
    results.append(save_pair(fig,p,'rainfall_daily',output_dir,'Meteorología: serie diaria y fechas desconocidas',caption='Conserva 7 faltantes; la línea se interrumpe, no se interpola ni se une a prismas.'))
    results.append(histogram(d.rainfall_mm,'rainfall_distribution','Meteorología: distribución de días medidos',output_dir,'Precipitación reportada (mm)',caption='Los días desconocidos quedan fuera de la distribución; ceros medidos se conservan.'))
    fig,ax=plt.subplots(figsize=(13,6));colors=[GOLD if x else BLUE for x in monthly.incomplete_month];ax.bar(monthly.month,monthly.observed_rainfall_total_mm,color=colors);ax.tick_params(axis='x',rotation=90);ax.set_ylabel('Suma de días observados (mm)')
    p=go.Figure(go.Bar(x=monthly.month,y=monthly.observed_rainfall_total_mm,marker_color=colors,customdata=monthly[['measured_days','missing_days','warning']],hovertemplate='%{x}: %{y} mm<br>Días medidos: %{customdata[0]}<br>Faltantes: %{customdata[1]}<br>%{customdata[2]}<extra></extra>'))
    results.append(save_pair(fig,p,'rainfall_monthly',output_dir,'Meteorología: totales observados por mes',caption='Amarillo: mes incompleto; su suma es parcial y no un total completamente observado.'))
    results.append(bar_plot(monthly.month,monthly.rainy_days_observed,'rainfall_rainy_days','Meteorología: días lluviosos observados por mes',output_dir,'Días con lluvia > 0',caption='No incluye días desconocidos; conservar cobertura mensual al comparar.'))
    fig,ax=plt.subplots(figsize=(13,4));ax.scatter(unknown.timestamp,np.ones(len(unknown)),marker='x',color=GOLD);ax.set_yticks([1],['Medición desconocida']);ax.set_xlim(d.timestamp.min(),d.timestamp.max())
    p=go.Figure(go.Scatter(x=unknown.timestamp,y=np.ones(len(unknown)),mode='markers',name='Fechas sin medición',marker={'symbol':'x','color':GOLD}))
    results.append(save_pair(fig,p,'rainfall_missing_dates',output_dir,'Meteorología: siete fechas con lluvia desconocida',caption='Las fechas se conservan, sin asignar lluvia cero.'))
    return results


def events_plots(data,output_dir):
    results=[]
    for c,title,unit in [('local_magnitude','magnitud local','Magnitud local reportada'),('potency_m3','Potency reportada','Potency reportada (m³)')]:
        results.append(histogram(data[c],'events_distribution_'+c,'Catálogo mixto: distribución de '+title,output_dir,unit,caption='Sin etiquetas sismo/voladura; definición operacional de Potency pendiente.'))
    fig,ax=plt.subplots(figsize=(13,6));ax.scatter(data.timestamp,data.local_magnitude,s=5,color=BLUE);ax.set_ylabel('Magnitud local')
    p=go.Figure(go.Scatter(x=data.timestamp,y=data.local_magnitude,mode='markers',marker={'color':BLUE,'size':4},name='Eventos del catálogo'))
    results.append(save_pair(fig,p,'events_timeline',output_dir,'Catálogo mixto: fechas y magnitud, interpretación Unix/UTC',caption='No se compara con prismas sin reloj validado ni se identifica automáticamente la voladura del artículo.'))
    fig,ax=plt.subplots(figsize=(12,7));ax.scatter(data.loc_e_m,data.loc_n_m,s=5,color=BLUE);ax.set_xlabel('LocE [m], CRS pendiente');ax.set_ylabel('LocN [m], CRS pendiente')
    p=go.Figure(go.Scatter3d(x=data.loc_e_m,y=data.loc_n_m,z=data.loc_u_m,mode='markers',marker={'size':2,'color':data.local_magnitude,'colorscale':'Blues'},text=data.timestamp.astype(str)))
    p.update_layout(scene={'xaxis_title':'LocE [m]','yaxis_title':'LocN [m]','zaxis_title':'LocU [m] (datum pendiente)'})
    results.append(save_pair(fig,p,'events_spatial',output_dir,'Catálogo mixto: cobertura espacial; CRS/datum pendientes',caption='PNG en planta; HTML muestra los 3 componentes reportados, sin convertir coordenadas.'))
    return results


def velocity_plot(data,output_dir):
    c='reported_velocity_change_pct';plus='reported_velocity_change_plus_sd_pct';minus='reported_velocity_change_minus_sd_pct';d=data.sort_values('timestamp')
    fig,ax=plt.subplots(figsize=(13,6));ax.plot(d.timestamp,d[c],color=BLUE);ax.fill_between(d.timestamp,d[minus],d[plus],color=CYAN,alpha=.25);ax.set_ylabel('Cambio de velocidad sísmica reportado (%)')
    p=go.Figure();p.add_trace(go.Scatter(x=d.timestamp,y=d[minus],line_width=0,name='Banda inferior reportada'))
    p.add_trace(go.Scatter(x=d.timestamp,y=d[plus],fill='tonexty',line_width=0,name='Banda superior reportada'))
    p.add_trace(go.Scatter(x=d.timestamp,y=d[c],name='Cambio sísmico reportado',line_color=BLUE))
    return save_pair(fig,p,'seismic_velocity_series',output_dir,'TXT: cambio de velocidad sísmica y bandas reportadas',caption='Contexto del artículo; sin prisma. No es velocidad de desplazamiento ni etiqueta de falla. Cadencia adjunta 48 h 50 min; no asumir 48 h.',height=700)
