import csv
import glob
import os
from pathlib import Path

def find_latest(pattern: str) -> str:
    """Return the most recently modified file matching the glob pattern."""
    candidates = glob.glob(pattern)
    if not candidates:
        raise FileNotFoundError(f"No files match pattern: {pattern}")
    return max(candidates, key=os.path.getmtime)


def load_route53(route53_file: str) -> list[dict]:
    records = []
    with open(route53_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            for ip in [ip.strip() for ip in row['Values'].split(';') if ip.strip()]:
                records.append({
                    'AccountId':  row['AccountId'],
                    'ZoneName':   row['ZoneName'],
                    'ZoneId':     row['ZoneId'],
                    'RecordName': row['RecordName'],
                    'IP':         ip
                })
    return records


def load_ipam(ipam_file: str) -> set:
    ips = set()
    with open(ipam_file, newline='') as f:
        for row in csv.DictReader(f):
            ips.add(row.get('IpAddress'))
    return ips


def load_eni(eni_file: str) -> tuple[set, set]:
    pub, priv = set(), set()
    with open(eni_file, newline='') as f:
        for row in csv.DictReader(f):
            if (p := row.get('PublicIPs')) and p != 'None':
                pub.add(p)
            priv.update([x.strip() for x in row.get('PrivateIPs', '').split(';') if x.strip()])
    return pub, priv


def main(base_folder: str = None):
    """
    If base_folder is provided, change into it and operate there.
    Otherwise uses the current working directory.
    """
    prev_cwd = os.getcwd()
    if base_folder:
        os.chdir(base_folder)
    try:
        route53_csv = find_latest('route53_a_records_*.csv')
        ipam_csv    = find_latest('global_public_ipv4_*.csv')
        eni_csv     = find_latest('enis_*.csv')
        out_file    = 'ip_lookup_results.csv'

        route53_recs = load_route53(route53_csv)
        ipam_ips      = load_ipam(ipam_csv)
        eni_pub, eni_priv = load_eni(eni_csv)

        with open(out_file, 'w', newline='') as f:
            fieldnames = [
                'AccountId', 'ZoneName', 'ZoneId', 'RecordName', 'IP',
                'IPAM_Association', 'ENI_Association'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in route53_recs:
                ip = rec['IP']
                ipam_assoc = 'Associated' if ip in ipam_ips else 'Not associated'
                eni_assoc  = 'Associated' if (ip in eni_pub or ip in eni_priv) else 'Not associated'
                writer.writerow({**rec,
                                 'IPAM_Association': ipam_assoc,
                                 'ENI_Association':  eni_assoc})

        print(f"Found:\n  Route53: {route53_csv}\n  IPAM:    {ipam_csv}\n  ENI:     {eni_csv}")
        print(f"Results written to {Path(os.getcwd()) / out_file}")
    finally:
        if base_folder:
            os.chdir(prev_cwd)


if __name__ == '__main__':
    main()
