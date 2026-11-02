"""Lectura controlada: no escribe en las fuentes ni deduce unidades."""
from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import io
import re
import zipfile
from datetime import date, datetime, time
import pandas as pd
from .schemas import clean_header, infer_kind, get_schema

SUPPORTED_EXTENSIONS={'.csv','.xlsx','.xls','.dat','.txt'}
MAX_FILE_BYTES=32*1024*1024
MAX_ROWS=250_000
MAX_COLUMNS=256

class DataLoadError(ValueError):
    """Error de lectura comprensible, sin trazas ni rutas internas en el mensaje."""

@dataclass
class LoadedSource:
    frame: pd.DataFrame
    source_name: str
    source_sha256: str
    source_lines: tuple[int,...]
    kind: str | None
    metadata: dict


def safe_filename(name):
    basename=str(name).replace('\\','/').split('/')[-1]
    result=re.sub(r'[^A-Za-z0-9._-]+','_',basename).strip('._')
    return result[:150] or 'source'


def _detect(rows,kind,header_row,max_header_lines):
    if kind is not None: get_schema(kind)
    if header_row is not None:
        if not isinstance(header_row,int) or header_row<0 or header_row>=len(rows):
            raise DataLoadError('La fila de encabezado indicada no existe.')
        if not any(clean_header(x) for x in rows[header_row]):
            raise DataLoadError('El encabezado indicado está vacío.')
        return header_row
    for i,row in enumerate(rows[:max_header_lines]):
        header=[clean_header(x) for x in row]
        detected=infer_kind(header)
        is_dat=header==['%Prism','day','month','year','hour','minute','second','Easting','Northing','Height','Adjusted Distance Diff','Unadjusted Slope Distance Diff','Easting Diff','Northing Diff','Height Diff']
        if kind is None and (detected is not None or is_dat): return i
        if kind=='slope_dat' and is_dat: return i
        if kind is not None and set(get_schema(kind).columns).issubset(set(header)): return i
    raise DataLoadError('No se encontró un encabezado reconocido en el límite de búsqueda. Indique el tipo y una fila de encabezado explícita para diagnosticar columnas faltantes.')


def _excel_text(value):
    if value is None: return ''
    if isinstance(value,datetime): return value.isoformat(sep=' ')
    if isinstance(value,(date,time)): return value.isoformat()
    return str(value)


def load_file(path, *, source_kind=None, header_row=None, sheet_name=0,
              max_file_bytes=MAX_FILE_BYTES, max_header_lines=50, encoding='utf-8-sig',
              max_rows=MAX_ROWS, max_columns=MAX_COLUMNS):
    """header_row es índice 0-based de registros CSV o filas Excel (no líneas físicas).

    CSV/DAT/TXT conservan texto de las celdas; Excel conserva la representación
    del valor almacenado. Fórmulas Excel no se evalúan ni se sustituyen por cachés.
    source_lines conserva el inicio físico de cada registro, incluso multilínea.
    """
    p=Path(path)
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise DataLoadError('Extensión no permitida. Use CSV, XLSX, XLS, DAT o TXT.')
    if not isinstance(max_header_lines,int) or max_header_lines<1:
        raise DataLoadError('El límite de búsqueda de encabezado debe ser positivo.')
    try:
        if not p.is_file(): raise DataLoadError('No se encontró un archivo de entrada válido.')
        if p.stat().st_size>max_file_bytes: raise DataLoadError('El archivo supera el tamaño máximo permitido.')
        content=p.read_bytes()
        if len(content)>max_file_bytes: raise DataLoadError('El archivo supera el tamaño máximo permitido.')
        if not content: raise DataLoadError('El archivo está vacío.')
        ext=p.suffix.lower(); rows=[]; source_lines=[]; metadata={'extension':ext,'size_bytes':len(content),'header_search_limit':max_header_lines}
        if ext in {'.csv','.dat','.txt'}:
            text=content.decode(encoding)
            if '\x00' in text: raise DataLoadError('El archivo de texto contiene bytes nulos; formato incompatible.')
            delimiter='\t' if ext=='.txt' else ','
            reader=csv.reader(io.StringIO(text,newline=''),delimiter=delimiter,strict=True)
            previous_line=0
            for row in reader:
                source_lines.append(previous_line+1); previous_line=reader.line_num; rows.append(row)
                if len(row)>max_columns: raise DataLoadError('Se excedió el límite de columnas.')
                if len(rows)>max_rows+max_header_lines+1: raise DataLoadError('Se excedió el límite de registros.')
            metadata.update(encoding=encoding,delimiter=delimiter,sheet=None)
        else:
            if ext=='.xlsx':
                from openpyxl import load_workbook
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    if sum(i.file_size for i in z.infolist())>128*1024*1024:
                        raise DataLoadError('El contenido Excel descomprimido supera el límite permitido.')
                book=load_workbook(io.BytesIO(content),read_only=True,data_only=False)
                try:
                    if isinstance(sheet_name,int): sheet=book.worksheets[sheet_name]
                    else: sheet=book[sheet_name]
                    metadata.update(sheet=sheet.title,encoding=None,delimiter=None,excel_values='stored values; formulas not evaluated')
                    # No depender de una dimensión declarada excesiva en Excel.
                    for row in sheet.iter_rows():
                        if len(row)>max_columns: raise DataLoadError('Se excedió el límite de columnas.')
                        values=[_excel_text(c.value) for c in row]
                        rows.append(values); source_lines.append(len(rows))
                        if len(rows)>max_rows+max_header_lines+1: raise DataLoadError('Se excedió el límite de registros.')
                finally: book.close()
            else:
                import xlrd
                book=xlrd.open_workbook(file_contents=content)
                sheet=book.sheet_by_index(sheet_name) if isinstance(sheet_name,int) else book.sheet_by_name(sheet_name)
                if sheet.nrows>max_rows+max_header_lines+1 or sheet.ncols>max_columns:
                    raise DataLoadError('Se excedieron los límites de filas o columnas Excel.')
                for i in range(sheet.nrows):
                    values=[]
                    for cell in sheet.row(i):
                        v=xlrd.xldate.xldate_as_datetime(cell.value,book.datemode) if cell.ctype==xlrd.XL_CELL_DATE else cell.value
                        if cell.ctype==xlrd.XL_CELL_DATE and cell.value<1: v=v.time()
                        values.append(_excel_text(v))
                    rows.append(values); source_lines.append(i+1)
                metadata.update(sheet=sheet.name,encoding=None,delimiter=None,excel_values='stored values')
        if not rows: raise DataLoadError('El archivo no contiene registros.')
        header_index=_detect(rows,source_kind,header_row,max_header_lines)
        columns=rows[header_index][:]
        if ext in {'.xlsx','.xls'}:
            while columns and columns[-1]=='': columns.pop()
        if not columns or any(not clean_header(c) for c in columns):
            raise DataLoadError('Hay nombres de columna vacíos en el encabezado.')
        if len({clean_header(c) for c in columns})!=len(columns):
            raise DataLoadError('Hay nombres de columna repetidos en el encabezado.')
        dat_repair=columns[0]=='%Prism' and ext=='.dat'
        declared_columns=columns[:]
        if dat_repair:
            expected=['%Prism','day','month','year','hour','minute','second','Easting','Northing','Height','Adjusted Distance Diff','Unadjusted Slope Distance Diff','Easting Diff','Northing Diff','Height Diff']
            if [clean_header(c) for c in columns]!=expected:
                raise DataLoadError('El encabezado DAT no coincide con la corrección documentada.')
            columns=['prism_part_1','prism_part_2']+columns[1:]
        values=[]; lines=[]; skipped_blank=[]
        for i,row in enumerate(rows[header_index+1:],header_index+1):
            if not row:
                skipped_blank.append(source_lines[i]); continue
            if ext in {'.xlsx','.xls'}:
                if any(x!='' for x in row[len(columns):]): raise DataLoadError('Excel contiene celdas fuera del encabezado reconocido.')
                row=row[:len(columns)]+['']*max(0,len(columns)-len(row))
            if len(row)!=len(columns):
                raise DataLoadError(f'Registro de ancho incorrecto en línea/fila {source_lines[i]}: {len(row)} campos, se esperaban {len(columns)}.')
            if len(values)>=max_rows: raise DataLoadError('Se excedió el límite de registros.')
            values.append(row); lines.append(source_lines[i])
        if not values: raise DataLoadError('No hay filas de datos después del encabezado.')
        kind=source_kind or infer_kind(columns)
        metadata.update(header_row_0based=header_index,header_line_1based=source_lines[header_index],
                        declared_columns=declared_columns,loaded_columns=columns,dat_header_repair=dat_repair,
                        skipped_blank_source_lines=skipped_blank,ignored_preamble=rows[:header_index])
        return LoadedSource(pd.DataFrame(values,columns=columns),p.name,hashlib.sha256(content).hexdigest(),tuple(lines),kind,metadata)
    except DataLoadError: raise
    except UnicodeError as e: raise DataLoadError('No se pudo decodificar el archivo con la codificación indicada.') from e
    except (OSError,ValueError,KeyError,IndexError,csv.Error,zipfile.BadZipFile,ImportError) as e:
        raise DataLoadError('No se pudo leer el archivo. Revise su formato, hoja, encabezado y dependencias Excel.') from e
    except Exception as e:
        # Los mensajes públicos no muestran celdas ni rutas potencialmente sensibles.
        raise DataLoadError('El contenido no es compatible con el formato de archivo indicado.') from e
