"""Preparación auditable sin uniones, imputación, interpolación ni unidades inferidas."""
from dataclasses import dataclass
import hashlib
import json
import numpy as np
import pandas as pd
from .data_loader import LoadedSource
from .data_validation import build_timestamp, missing_mask, text_series, validate_data
from .schemas import column_mapping, get_schema

@dataclass
class PreparedSource:
    data: pd.DataFrame
    excluded: pd.DataFrame
    originals: pd.DataFrame
    dispositions: pd.DataFrame
    journal: list[dict]
    quality_before: dict
    quality_after: dict
    metadata: dict


def fingerprint(frame):
    """Huella sobre contenido y orden; mantiene distintas las ausencias y texto vacío."""
    values=pd.util.hash_pandas_object(frame,index=False).to_numpy().tobytes()
    columns=json.dumps(list(frame.columns),ensure_ascii=False).encode()
    return hashlib.sha256(columns+values).hexdigest()


def prepare_source(loaded:LoadedSource,*,min_observations=20):
    kind=loaded.kind
    schema=get_schema(kind)
    source=loaded.frame.copy(deep=True).reset_index(drop=True)
    if len(source)!=len(loaded.source_lines): raise ValueError('El número de filas no coincide con la trazabilidad de origen.')
    before=validate_data(source,kind,min_observations=min_observations)
    if before.metrics['required_missing_columns']:
        raise ValueError('Faltan columnas obligatorias: '+', '.join(before.metrics['required_missing_columns']))
    mapping=column_mapping(source.columns,kind)
    reserved={'row_id','source_name','source_sha256','source_line','timestamp','quality_flags','exclusion_reason','retained_row_id'}
    if reserved & set(mapping.values()) or any(x.startswith('original__') for x in mapping.values()):
        raise ValueError('Una columna de entrada colisiona con campos reservados de trazabilidad.')
    sheet=loaded.metadata.get('sheet')
    row_ids=[hashlib.sha256(f'{loaded.source_sha256}|{sheet}|{line}'.encode()).hexdigest() for line in loaded.source_lines]
    originals=source.copy(deep=True)
    originals.insert(0,'row_id',row_ids)
    originals.insert(1,'source_line',loaded.source_lines)
    df=source.copy(deep=True)
    journal=[]
    def record(operation,before_state,after_state,affected,**details):
        journal.append({'step':len(journal)+1,'operation':operation,'rows_affected':int(affected),
                        'before':{'rows':len(before_state),'columns':list(before_state.columns),'fingerprint':fingerprint(before_state)},
                        'after':{'rows':len(after_state),'columns':list(after_state.columns),'fingerprint':fingerprint(after_state)},
                        'details':details})
    # Loader decisions are transformations of representation, with originals in data/raw.
    journal.append({'step':1,'operation':'controlled_read','rows_affected':len(df),
                    'before':{'source_sha256':loaded.source_sha256,'declared_columns':loaded.metadata['declared_columns']},
                    'after':{'rows':len(df),'loaded_columns':list(df.columns),'fingerprint':fingerprint(df)},
                    'details':loaded.metadata})
    prior=df.copy(deep=True); df=df.rename(columns=mapping)
    record('normalize_column_names',prior,df,len(df),column_mapping=mapping,values_changed=False)
    prior=df.copy(deep=True)
    for column in list(df.columns): df['original__'+column]=df[column].copy(deep=True)
    df['row_id']=row_ids; df['source_line']=loaded.source_lines
    df['source_name']=loaded.source_name; df['source_sha256']=loaded.source_sha256
    record('preserve_original_values_and_add_provenance',prior,df,len(df),
           row_id_rule='SHA256(file_sha256 | Excel_sheet_or_None | physical_start_line)',
           before_values='original_rows.csv: row_id and original source columns',
           after_values='active/excluded CSV: original__<normalized column>, unchanged source value')
    corrected=pd.Series(False,index=df.index)
    # Explicit type conversions: invalids remain auditable in original__ columns.
    invalid_numeric={}
    for column in schema.numeric:
        prior=df.copy(deep=True)
        empty=missing_mask(df[column]); numbers=pd.to_numeric(df[column],errors='coerce')
        bad=~empty & (numbers.isna()|~np.isfinite(numbers))
        invalid_numeric[column]=bad
        df[column]=numbers.where(np.isfinite(numbers))
        record('parse_numeric_column',prior,df,len(df),column=column,nonempty_values=int((~empty).sum()),invalid_count=int(bad.sum()),
               unknown_count=int(empty.sum()),before_column='original__'+column,after_column=column,
               before_after_lookup='row_id in original_rows.csv and active/excluded CSV',
               invalid_policy='Retener y marcar; valor tipado desconocido, original intacto.',units=schema.units.get(column,'componente calendario'))
    if kind=='slope_dat':
        prior=df.copy(deep=True)
        df['prism_id']=text_series(df['prism_part_1'])+'-'+text_series(df['prism_part_2'])
        df.loc[missing_mask(df['prism_part_1'])|missing_mask(df['prism_part_2']),'prism_id']=pd.NA
        record('compose_prism_id',prior,df,len(df),rule='part_1 + hyphen + part_2; documentado por cotejo con CSV')
    identity='prism_id' if 'prism_id' in schema.keys else 'station_id' if 'station_id' in schema.keys else None
    if identity:
        prior=df.copy(deep=True); old=df[identity].copy(); df[identity]=text_series(old).replace('',pd.NA)
        changed=(old.fillna('')!=df[identity].fillna('')) | (old.notna() & df[identity].isna())
        corrected|=changed
        record('normalize_identifier_whitespace',prior,df,int(changed.sum()),column=identity,
               before_column='original__'+identity if kind!='slope_dat' else 'prism_part_1, prism_part_2',
               after_column=identity,retain_leading_zeros=True,replace_missing_with='unknown (not string nan)')
    prior=df.copy(deep=True); df['timestamp']=build_timestamp(df,kind)
    record('construct_timestamp',prior,df,len(df),time_basis=schema.time_basis,
           source_columns='date_original+time_original; or explicit year/month/day; or ISO/epoch per schema',
           two_digit_year_policy='2000–2099 for DD-Mon-YY and DAT, explicit policy for this dataset; no locale dependency',
           conversions='No time-zone conversion for prism/weather/TXT. No resampling, offsets, interpolation or physical units conversion.')
    flags=[[] for _ in range(len(df))]
    for column in schema.columns.values():
        original='original__'+column
        miss=missing_mask(df[original])
        for i in np.flatnonzero(miss): flags[i].append('missing:'+column)
    for column,mask in invalid_numeric.items():
        for i in np.flatnonzero(mask): flags[i].append('invalid_numeric:'+column)
    invalid_time=df['timestamp'].isna()
    invalid_id=missing_mask(df[identity]) if identity else pd.Series(False,index=df.index)
    for i in np.flatnonzero(invalid_time): flags[i].append('invalid_timestamp')
    for i in np.flatnonzero(invalid_id): flags[i].append('missing_identifier')
    if kind=='rainfall':
        bad=(df['rainfall_mm'].notna()&df['rainfall_mm'].lt(0)) | (df['rainfall_period_days'].notna()&(~df['rainfall_period_days'].gt(0)|~df['rainfall_period_days'].eq(df['rainfall_period_days'].round())))
        for i in np.flatnonzero(bad): flags[i].append('rainfall_semantics_requires_review')
    prior=df.copy(deep=True); df['quality_flags']=[';'.join(f) for f in flags]
    record('flag_unknown_invalid_values',prior,df,int(df.quality_flags.ne('').sum()),
           policy='Marcar sin descartar extremos; conservar lluvia desconocida y códigos originales.')
    reasons=pd.Series('',index=df.index,dtype='string'); links=pd.Series('',index=df.index,dtype='string')
    # Only exact source-cell duplicates removed. First physical occurrence is tie-break.
    original_columns=['original__'+x for x in mapping.values()]
    exact=df.duplicated(original_columns,keep='first')
    if exact.any():
        # Duplicate groups can be noncontiguous; recover the retained row without numeric coercion.
        duplicate_group=df.loc[df.duplicated(original_columns,keep=False)]
        groups=duplicate_group.groupby(original_columns,dropna=False,sort=False).groups
        for positions in groups.values():
            if len(positions)>1:
                keep=int(positions[0])
                for i in positions[1:]: reasons.iloc[i]='exact_duplicate'; links.iloc[i]=df.iloc[keep]['row_id']
    prior=df.copy(deep=True); remaining=df.loc[~exact].copy()
    record('exclude_exact_duplicates',prior,remaining,int(exact.sum()),
           policy='Se conserva primera ocurrencia física; desempate de registros idénticos, no corte temporal.',
           excluded_evidence='excluded_rows.csv contains original values, row_id, source_line, reason and retained_row_id')
    invalid=(invalid_time|invalid_id)&~exact
    reasons.loc[invalid]=[';'.join(x for x,yes in [('invalid_timestamp',invalid_time[i]),('missing_identifier',invalid_id[i])] if yes) for i in reasons.index[invalid]]
    prior=remaining.copy(deep=True); remaining=remaining.loc[~invalid.loc[remaining.index]].copy()
    record('quarantine_unusable_keys',prior,remaining,int(invalid.sum()),
           policy='Solo fechas o IDs esenciales no utilizables: conservar en excluded_rows.csv para corrección; no borrar originales.')
    # Conflicting repeated times are not merged or arbitrarily selected.
    conflict=remaining.duplicated(list(schema.keys),keep=False)
    reasons.loc[remaining.index[conflict]]='conflicting_key_requires_review'
    prior=remaining.copy(deep=True); remaining=remaining.loc[~conflict].copy()
    record('quarantine_conflicting_keys',prior,remaining,int(conflict.sum()),
           policy='Todas las filas de una clave contradictoria se conservan fuera de la salida activa para revisión; ninguna se elige arbitrariamente.')
    prior=remaining.copy(deep=True)
    order=([identity] if identity else [])+['timestamp','row_id']
    remaining=remaining.sort_values(order,kind='stable')
    moved=sum(a!=b for a,b in zip(prior.row_id,remaining.row_id))
    record('sort_by_identifier_and_timestamp',prior,remaining,moved,sort_columns=order,
           before_order='row_dispositions.csv: source_line',after_order='row_dispositions.csv: processed_position',
           temporal_policy='Todos los ordenamientos/cortes temporales usan timestamp; no hay cortes de entrenamiento en Fase 2.')
    if identity=='prism_id':
        counts=remaining.groupby('prism_id')['timestamp'].nunique(); small=set(counts[counts<min_observations].index)
        prior=remaining.copy(deep=True); mask=remaining.prism_id.isin(small)
        remaining.loc[mask,'quality_flags']=remaining.loc[mask,'quality_flags'].apply(lambda x: (x+';' if x else '')+'insufficient_observations')
        record('flag_insufficient_prism_observations',prior,remaining,int(mask.sum()),threshold=min_observations,
               note='Mínimo operativo configurable, no umbral de estabilidad ni motivo de exclusión.')
    excluded=df.loc[reasons.ne('')].copy(); excluded['exclusion_reason']=reasons.loc[excluded.index]; excluded['retained_row_id']=links.loc[excluded.index]
    # No values transformed after typing; active/excluded contain final and original values.
    dispositions=pd.DataFrame({'row_id':row_ids,'source_line':loaded.source_lines,'status':np.where(reasons.ne(''),'excluded','retained'),
                               'reason':reasons,'retained_row_id':links,'corrected_identifier':corrected,
                               'quality_flags':df['quality_flags']})
    dispositions.loc[remaining.index,'quality_flags']=remaining['quality_flags']
    positions={rid:i for i,rid in enumerate(remaining.row_id)}
    dispositions['processed_position']=dispositions.row_id.map(positions).astype('Int64')
    after=validate_data(remaining.reset_index(drop=True),kind,normalized=True,min_observations=min_observations)
    if after.metrics['invalid_timestamps'] or after.metrics['missing_identifiers'] or after.metrics['zero_intervals']:
        raise RuntimeError('La salida activa no satisface claves válidas e intervalos no nulos.')
    marked=remaining.quality_flags.ne('')
    summary={'input_rows':len(source),'retained_rows':len(remaining),'excluded_rows':len(excluded),
             'exact_duplicate_excluded_rows':int(reasons.eq('exact_duplicate').sum()),
             'quarantined_invalid_key_rows':int(invalid.sum()),'quarantined_conflicting_key_rows':int(conflict.sum()),
             'corrected_identifier_rows':int((corrected & reasons.eq('')).sum()),
             'marked_retained_rows':int(marked.sum()),'reordered_rows':int(moved),
             'new_timestamp_rows':len(df),'numeric_columns_parsed':list(schema.numeric),
             'note':'Normalización de nombres, tipado y columnas derivadas afectan la representación de todas las filas; no son correcciones físicas. Marcadas/corregidas son subconjuntos de conservadas.'}
    metadata={'source_kind':kind,'source_name':loaded.source_name,'source_sha256':loaded.source_sha256,
              'schema_mapping':mapping,'loader_metadata':loaded.metadata,'units':schema.units,
              'description':schema.description,'time_basis':schema.time_basis,'summary':summary,
              'audit_reconstruction':'Original + tipado por row_id: original_rows.csv y active/excluded CSV; orden por row_dispositions.csv; nombres y políticas por transformations.jsonl.',
              'physical_derivatives_calculated':False,'sources_joined':False,'imputation':False,'interpolation':False,
              'csv_reload_note':'CSV no transporta dtypes: leer station_id/prism_id/original__* como texto; usar metadata. Valores numéricos faltantes se exportan vacíos, semántica unknown.'}
    return PreparedSource(remaining.reset_index(drop=True),excluded.reset_index(drop=True),originals,dispositions,journal,before.to_dict(),after.to_dict(),metadata)


def export_prepared(result:PreparedSource,output_dir):
    from pathlib import Path
    directory=Path(output_dir)
    if any(part=='raw' for part in directory.resolve().parts):
        raise ValueError('Está prohibido exportar dentro de un directorio raw.')
    directory.mkdir(parents=True,exist_ok=True)
    result.data.to_csv(directory/'data.csv',index=False)
    result.excluded.to_csv(directory/'excluded_rows.csv',index=False)
    result.originals.to_csv(directory/'original_rows.csv',index=False)
    result.dispositions.to_csv(directory/'row_dispositions.csv',index=False)
    for name,data in [('metadata.json',result.metadata),('quality_before.json',result.quality_before),('quality_after.json',result.quality_after)]:
        (directory/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (directory/'transformations.jsonl').write_text(''.join(json.dumps(event,ensure_ascii=False)+'\n' for event in result.journal),encoding='utf-8')
