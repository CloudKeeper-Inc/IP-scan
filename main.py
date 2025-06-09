import os
import sys
import datetime
import csv

import ipam.ipam as ipam
import route53.route53 as route53
import eni.fetch_eni  as eni_mod
import searchIP.search_ip as search_ip
from config.config import ACCOUNTS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

today_folder = os.path.join(
    BASE_DIR,
    datetime.datetime.now().strftime('%Y-%m-%d')
)
os.makedirs(today_folder, exist_ok=True)


def save_to_csv(filename: str, records: list[dict], fieldnames: list[str]):
    """Write a list of dicts to CSV file inside today_folder."""
    if not records:
        print(f"[!] No records to write for {filename}")
        return
    out_path = os.path.join(today_folder, filename)
    try:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"[+] Wrote {len(records)} records to {out_path}")
    except Exception as e:
        print(f"[✗] Failed to write {out_path}: {e}", file=sys.stderr)
        sys.exit(1)


def run_ipam():
    ts    = datetime.datetime.now().strftime('%Y-%m-%d')
    fname = f"global_public_ipv4_{ts}.csv"
    all_public = []
    for acct in ACCOUNTS:
        sess = ipam.get_session(acct['id'], acct['role'])
        data = ipam.fetch_public_ipv4_addresses_global(
            sess, acct['id'], acct['ipam_region']
        )
        all_public.extend(data)
    headers = list(all_public[0].keys()) if all_public else []
    save_to_csv(fname, all_public, headers)


def run_eni():
    ts    = datetime.datetime.now().strftime('%Y-%m-%d')
    fname = f"enis_{ts}.csv"
    all_enis = []
    for acct in ACCOUNTS:
        sess = eni_mod.get_session(acct['id'], acct['role'])
        for region in acct['eni_regions']:
            all_enis.extend(
                eni_mod.fetch_enis(sess, acct['id'], region)
            )
    headers = ["Account", "Region", "ENI_ID", "PrivateIPs", "PublicIPs"]
    save_to_csv(fname, all_enis, headers)


def run_route53():
    ts    = datetime.datetime.now().strftime('%Y-%m-%d')
    fname = f"route53_a_records_{ts}.csv"
    all_rr = []
    for acct in ACCOUNTS:
        sess = route53.get_session(acct['id'], acct['role'])
        all_rr.extend(route53.fetch_a_records(sess, acct['id']))
    headers = ["AccountId", "ZoneName", "ZoneId", "RecordName", "Values"]
    save_to_csv(fname, all_rr, headers)


def run_search_ip():
    prev_cwd = os.getcwd()
    os.chdir(today_folder)
    try:
        search_ip.main()
    finally:
        os.chdir(prev_cwd)


def main():
    run_ipam()
    run_eni()
    run_route53()
    run_search_ip()


if __name__ == '__main__':
    main()
