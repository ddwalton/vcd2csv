import argparse
import csv
import os
import re

def get_field(f, line, field):
    val = line.lstrip(field).rstrip('$end\n').strip()
    while line.find('$end') < 0:
        val = line.rstrip('$end\n').strip()
        line = f.readline()
    return val


def vcd2csv(infile, outfile, en_scope=False):
    """
    Convert a VCD (Value Change Dump) file into CSV format.

    Parameters
    ----------
    infile : str
        Path to the input VCD file.
    outfile : str
        Path where the CSV file will be written.
    en_scope : bool, optional (default=False)
        If True, include full hierarchical signal scope names in the CSV output.
        If False, only signal names will be used.
    """     
    keys = ['ts']
    ref = ['timestamp']
    scope = ''

    vd = re.compile(r'^\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(.+?)\s*\$end')
    sc = re.compile(r'^\$scope\s+\S+\s+(\S+)\s+\$end')
    us = re.compile(r'^\$upscope')

    with open(infile, 'r') as f:
        print('Writing to file:', outfile)
        w = open(outfile, 'w', newline='')
        wcsv = csv.writer(w)

        while True:
            line = f.readline()
            if not line:
                break
            line_s = line.strip()

            if line_s.startswith('$timescale'):
                timescale = get_field(f, line, '$timescale')
            elif line_s.startswith('$date'):
                date = get_field(f, line, '$date')
            elif line_s.startswith('$version'):
                version = get_field(f, line, '$version')

            if line_s.startswith('$var'):
                m = vd.match(line_s)
                if m:
                    keys.append(m.group(3))
                    sig_name = m.group(4).strip()
                    if en_scope and scope:
                        ref.append(f"{scope}.{sig_name}")
                    else:
                        ref.append(sig_name)
                else:
                    print('Error on parsing variable declaration:', line_s)

            elif line_s.startswith('$scope'):
                m = sc.match(line_s)
                if m:
                    scope = f"{scope}.{m.group(1)}" if scope else m.group(1)
                else:
                    print('Error in parsing module name:', line_s)

            elif us.match(line_s):
                if '.' in scope:
                    scope = scope.rsplit('.', 1)[0]
                else:
                    scope = ''

            elif line_s.startswith('$enddefinitions'):
                wcsv.writerow(ref)
                break

        d = dict.fromkeys(keys, None)

        # Locate signal symbol ID corresponding to 'clk' or 'clock'
        clk_id = None
        for k, r in zip(keys[1:], ref[1:]):
            clean_name = r.split('.')[-1].split('[')[0].strip().lower()
            if clean_name in ['clk', 'clock']:
                clk_id = k
                break

        sb = re.compile(r'^([01xXzZ])(\S+)$')
        bv = re.compile(r'^[bB](\S+)\s+(\S+)$')
        rv = re.compile(r'^[rR](\S+)\s+(\S+)$')

        def write_row():
            if d['ts'] is not None:
                if clk_id is None or d.get(clk_id) == 1:
                    wcsv.writerow([d[k] for k in keys])

        while True:
            line = f.readline()
            if not line:
                break
            line_s = line.strip()
            if line_s.startswith('#'):
                d['ts'] = int(line_s[1:])
                break

        while line:
            line = f.readline()
            if not line:
                break
            line_s = line.strip()

            if not line_s or line_s.startswith('$'):
                continue

            if line_s.startswith('#'):
                write_row()
                d['ts'] = int(line_s[1:])
                continue

            m = sb.match(line_s)
            if m:
                val = m.group(1)
                try:
                    val = int(val, 2)
                except ValueError:
                    pass
                d[m.group(2)] = val
                continue

            m = bv.match(line_s)
            if m:
                val_str = m.group(1)
                try:
                    val = int(val_str, 2)
                except ValueError:
                    val = val_str
                d[m.group(2)] = val
                continue

            m = rv.match(line_s)
            if m:
                val_str = m.group(1)
                try:
                    val = float(val_str)
                except ValueError:
                    val = val_str
                d[m.group(2)] = val
                continue

        write_row()
        w.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert VCD waveform file to CSV.")
    parser.add_argument("vcd_path", help="Path to the input VCD file")
    parser.add_argument("csv_path", nargs="?", help="Path to output CSV file (optional)")
    parser.add_argument("--en-scope", action="store_true", help="Include full hierarchical signal scope names")

    args = parser.parse_args()

    vcd_path = args.vcd_path
    csv_path = args.csv_path if args.csv_path else os.path.splitext(vcd_path)[0] + ".csv"

    vcd2csv(vcd_path, csv_path, en_scope=args.en_scope)