from pathlib import Path
import csv
import pytest
from src.schemas import WEST, SOUTH, RAIN

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def raw_dir(): return ROOT/'data/raw'

@pytest.fixture
def west_rows():
    return [
        ['P-1','02-Jan-14','10:00:00','1','2','3','8'],
        ['P-1','01-Jan-14','10:00:00','1','2','3','10'],
        ['P-2','01-Jan-14','09:00:00','4','5','6','1000000000'],
    ]

@pytest.fixture
def west_file(tmp_path,west_rows):
    p=tmp_path/'west.csv'
    with p.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(WEST);w.writerows(west_rows)
    return p

@pytest.fixture
def write_table(tmp_path):
    def write(name,header,rows,delimiter=',',preamble=None):
        p=tmp_path/name
        with p.open('w',newline='',encoding='utf-8') as f:
            if preamble: f.write(preamble)
            w=csv.writer(f,delimiter=delimiter);w.writerow(header);w.writerows(rows)
        return p
    return write
