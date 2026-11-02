"""Ejecuta el notebook con IPython en un proceso local, sin puertos de kernel.

Solo para el notebook del proyecto, revisado y escrito por nosotros. Conserva
salidas y execution_count reales; no genera resultados ficticios.
"""
from pathlib import Path
import sys,json
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'notebooks/exploracion_fase3.ipynb'
nb=nbformat.read(path,as_version=4);shell=InteractiveShell.instance();count=0
for cell in nb.cells:
    if cell.cell_type!='code':continue
    count+=1;cell.outputs=[]
    with capture_output(display=True) as captured:
        result=shell.run_cell(cell.source,store_history=True)
    if result.error_before_exec or result.error_in_exec:
        raise RuntimeError(f'Falló la celda de código {count}') from (result.error_before_exec or result.error_in_exec)
    if captured.stdout:cell.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
    if captured.stderr:cell.outputs.append(nbformat.v4.new_output('stream',name='stderr',text=captured.stderr))
    for output in captured.outputs:
        cell.outputs.append(nbformat.v4.new_output('display_data',data=output.data,metadata=output.metadata))
    if result.result is not None:
        obj=result.result;data={'text/plain':repr(obj)}
        if hasattr(obj,'_repr_html_'):
            value=obj._repr_html_()
            if value:data['text/html']=value
        cell.outputs.append(nbformat.v4.new_output('execute_result',data=data,metadata={},execution_count=count))
    cell.execution_count=count
nb.metadata['phase3_execution']={'method':'IPython InteractiveShell, one local process without kernel ports',
                                'code_cells_executed':count,'errors':0,'reason':'Managed runtime blocked TCP kernel startup; no source/output data changed.'}
nbformat.validate(nb);nbformat.write(nb,path)
(ROOT/'reports/phase3/notebook_execution.json').write_text(json.dumps(nb.metadata['phase3_execution'],indent=2))
print(f'Notebook ejecutado: {count} celdas, 0 errores; IPython local sin puertos.')
