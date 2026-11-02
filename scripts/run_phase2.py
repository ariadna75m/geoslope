"""Prepara cuatro fuentes independientemente; aborta ante integridad alterada."""
from pathlib import Path
import hashlib,json,sys,time,platform
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.data_loader import load_file,DataLoadError
from src.preprocessing import prepare_source,export_prepared

RAW=ROOT/'data/raw'; PROCESSED=ROOT/'data/processed'; REPORTS=ROOT/'reports/phase2'
SOURCES=[
 ('west_wall','radar-deformation-data/West Wall Prism Movements - 3 months to 20-Feb-14.csv'),
 ('south_west','radar-deformation-data/South_West_Corner_06082014.csv'),
 ('rainfall_2013','weather-data/IDCJAC0009_029167_2013_Data.csv'),
 ('rainfall_2014','weather-data/IDCJAC0009_029167_2014_Data.csv'),
]


def verify_originals():
    manifest=json.loads((ROOT/'reports/original_manifest.json').read_text())
    for entry in manifest:
        p=RAW/entry['path']
        if p.stat().st_size!=entry['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('Falló la comprobación de integridad de un original; ejecución detenida.')
    return manifest


def main():
    REPORTS.mkdir(parents=True,exist_ok=True)
    originals=verify_originals(); comparisons=[]; outputs=[]; load_checks=[]; durations={}
    # CSV, DAT y TXT reales se prueban en lectura; PDF permanece como documentación.
    for entry in originals:
        p=RAW/entry['path']
        if p.suffix.lower()=='.pdf':continue
        loaded=load_file(p)
        load_checks.append({'source':entry['path'],'kind':loaded.kind,'rows':len(loaded.frame),
                            'columns':len(loaded.frame.columns),'header_line':loaded.metadata['header_line_1based'],
                            'source_sha256':loaded.source_sha256,'read_success':True})
    for name,relative in SOURCES:
        start=time.perf_counter();loaded=load_file(RAW/relative)
        result=prepare_source(loaded,min_observations=20)
        destination=PROCESSED/name;export_prepared(result,destination)
        summary=result.metadata['summary']; before=result.quality_before['metrics'];after=result.quality_after['metrics']
        comparisons.append({'source':name,**summary,'missing_cells_before':before['missing_cells'],'missing_cells_after':after['missing_cells'],
                            'missing_rain_before':before['missing_by_column'].get('rainfall_mm'),
                            'missing_rain_after':after['missing_by_column'].get('rainfall_mm'),
                            'duplicate_rows_before':before['duplicate_rows_extra'],'duplicate_rows_after':after['duplicate_rows_extra'],
                            'zero_intervals_before':before['zero_intervals'],'zero_intervals_after':after['zero_intervals'],
                            'invalid_timestamps_before':before['invalid_timestamps'],'invalid_timestamps_after':after['invalid_timestamps'],
                            'insufficient_prisms_before':len(before['insufficient_prisms']),'insufficient_prisms_after':len(after['insufficient_prisms']),
                            'errors_before':len(result.quality_before['errors']),'errors_after':len(result.quality_after['errors']),
                            'warnings_before':len(result.quality_before['warnings']),'warnings_after':len(result.quality_after['warnings'])})
        assert summary['retained_rows']+summary['excluded_rows']==summary['input_rows']
        assert result.data['row_id'].is_unique and result.originals['row_id'].is_unique
        assert set(result.data.row_id)|set(result.excluded.row_id)==set(result.originals.row_id)
        assert set(result.data.row_id).isdisjoint(set(result.excluded.row_id))
        # Verify field preservation against original input by stable identifier.
        all_rows=pd.concat([result.data,result.excluded],ignore_index=True).set_index('row_id')
        original_rows=result.originals.set_index('row_id')
        for source_column,normal_column in result.metadata['schema_mapping'].items():
            assert all_rows.loc[original_rows.index,'original__'+normal_column].equals(original_rows[source_column].rename('original__'+normal_column))
        for p in sorted(destination.iterdir()):
            outputs.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        durations[name]=round(time.perf_counter()-start,3)
        print(json.dumps({'source':name,**summary},ensure_ascii=False),flush=True)
    verify_originals()
    json_data={'phase':2,'sources_joined':False,'models_trained':False,'physical_features_calculated':False,
               'originals_verified_before_after':True,'original_count':len(originals),'comparison':comparisons,'load_checks':load_checks,
               'processed_output_files':outputs,'checkpoint_before_phase2':'2130e29',
               'runtime':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__},
               'operational_notes':'Fase 2 completa; Fase 3 pendiente de aprobación.'}
    (REPORTS/'summary.json').write_text(json.dumps(json_data,indent=2,ensure_ascii=False),encoding='utf-8')
    pd.DataFrame(comparisons).drop(columns=['numeric_columns_parsed','note']).to_csv(REPORTS/'quality_comparison.csv',index=False)
    # Non-deterministic timings stored separately; prepared files and summary reproducible.
    (REPORTS/'processing_times.json').write_text(json.dumps(durations,indent=2),encoding='utf-8')
    print('Integridad verificada: ocho originales; fuentes preparadas por separado.',flush=True)


if __name__=='__main__':
    try:main()
    except (DataLoadError,ValueError,RuntimeError) as exc:
        print('Fase 2 detenida: '+str(exc),file=sys.stderr);sys.exit(1)
