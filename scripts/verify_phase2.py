"""Aceptación sobre archivos exportados; --reproduce ejecuta la preparación dos veces."""
from pathlib import Path
import hashlib,json,sys,argparse
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from run_phase2 import main as prepare_all,verify_originals


def file_hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'data/processed').rglob('*')) if p.is_file()}


def verify(reproduce=False):
    if reproduce:
        prepare_all();first=file_hashes();prepare_all();second=file_hashes()
        if first!=second:raise RuntimeError('Las dos ejecuciones no produjeron archivos idénticos.')
        proof={'prepared_files_checked':len(first),'all_identical_between_two_runs':True,'sha256_by_file':second,
               'comparison':'byte-for-byte SHA256; processing_times intentionally excluded'}
        (ROOT/'reports/phase2/reproducibility.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
    verify_originals();summary=json.loads((ROOT/'reports/phase2/summary.json').read_text())
    evidence=[]
    for entry in summary['comparison']:
        source=entry['source'];directory=ROOT/'data/processed'/source
        read=lambda name:pd.read_csv(directory/name,dtype=str,keep_default_na=False)
        active=read('data.csv');excluded=read('excluded_rows.csv');original=read('original_rows.csv');disposition=read('row_dispositions.csv')
        both=pd.concat([active,excluded],ignore_index=True).set_index('row_id');raw=original.set_index('row_id')
        assert active.row_id.is_unique and original.row_id.is_unique
        assert set(active.row_id).isdisjoint(excluded.row_id)
        assert set(both.index)==set(raw.index)==set(disposition.row_id)
        metadata=json.loads((directory/'metadata.json').read_text())
        for a,b in metadata['schema_mapping'].items():
            assert both.loc[raw.index,'original__'+b].tolist()==raw[a].tolist()
        active['timestamp']=pd.to_datetime(active['timestamp'],errors='raise')
        identity='prism_id' if 'prism_id' in active else 'station_id'
        for _,group in active.groupby(identity):
            assert group.timestamp.is_monotonic_increasing
            assert not group.timestamp.duplicated().any()
        events=[json.loads(x) for x in (directory/'transformations.jsonl').read_text().splitlines()]
        for a,b in zip(events,events[1:]):
            assert a['after']['fingerprint']==b['before']['fingerprint']
        evidence.append({'source':source,'original_values_preserved':True,'rows_partitioned':True,
                         'timestamps_ordered_and_unique_per_id':True,'journal_fingerprint_chain_valid':True,'journal_steps':len(events)})
    proof=json.loads((ROOT/'reports/phase2/reproducibility.json').read_text())
    assert proof['sha256_by_file']==file_hashes()
    evidence_doc={'original_files_intact':8,'prepared_files_identical_across_runs':proof['prepared_files_checked'],
                  'sources':evidence,'errors':[]}
    (ROOT/'reports/phase2/acceptance_checks.json').write_text(json.dumps(evidence_doc,ensure_ascii=False,indent=2))
    print('Aceptación verificada: originales intactos; valores originales, partición de filas, orden temporal y cadena de auditoría correctos.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reproduce',action='store_true')
    verify(parser.parse_args().reproduce)
