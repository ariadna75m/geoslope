"""Verifica tablas, PNG, HTML local y archivos protegidos; reproducción opcional."""
from pathlib import Path
import sys,json,hashlib,argparse
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_phase3 import main as run,check_protected
OUT=ROOT/'reports/phase3'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main(reproduce=False):
    before=json.loads((OUT/'phase3_metadata.json').read_text())
    if reproduce:run()
    after=json.loads((OUT/'phase3_metadata.json').read_text())
    assert before['table_hashes']==after['table_hashes'],'Las tablas cambiaron al reproducir.'
    for name,h in after['table_hashes'].items():assert digest(OUT/name)==h,name
    js=OUT/'interactive/plotly.min.js';assert js.stat().st_size>1000
    for asset in after['figures']:
        with Image.open(OUT/asset['png']) as picture:picture.verify()
        html=(OUT/asset['html']).read_text()
        assert 'src="plotly.min.js"' in html and 'Plotly.newPlot' in html,asset['name']
        assert 'cdn.plot.ly' not in html,asset['name']
    proof={'tables_identical':True,'table_count':len(after['table_hashes']),'table_hashes':after['table_hashes'],
           'full_pipeline_repeated':reproduce,'protected_files_intact':check_protected(),
           'png_validated':len(after['figures']),'html_local_assets_validated':len(after['figures']),
           'plotly_js_sha256':digest(js),'checkpoint_before':after['checkpoint_before']}
    path=OUT/'reproducibility.json'
    # No perder prueba de una reproducción real al realizar después solo comprobaciones.
    if path.exists() and not reproduce:
        old=json.loads(path.read_text())
        if old.get('full_pipeline_repeated') and old.get('table_hashes')==proof['table_hashes']:proof['full_pipeline_repeated']=True
    path.write_text(json.dumps(proof,indent=2))
    print(f"{proof['table_count']} tablas idénticas; {proof['png_validated']} PNG válidos; {proof['protected_files_intact']} archivos anteriores intactos.")

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reproduce',action='store_true');args=parser.parse_args();main(args.reproduce)
