import boto3
import csv
import sys
import datetime

from config.config import ACCOUNTS


def get_session(account_id, role_name):
    """Assume the specified role and return a boto3 Session."""
    sts = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    resp = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=f"{role_name}-{account_id}-{datetime.datetime.now().timestamp()}"
    )
    creds = resp['Credentials']
    return boto3.Session(
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )


def fetch_a_records(session, account_id):
    """Fetch A records from all hosted zones for a given session and tag with account_id."""
    client = session.client('route53')
    records = []

    paginator_zones = client.get_paginator('list_hosted_zones')
    for zone_page in paginator_zones.paginate():
        for zone in zone_page['HostedZones']:
            zid = zone['Id'].split('/')[-1]
            zname = zone['Name'].rstrip('.')

            paginator_rr = client.get_paginator('list_resource_record_sets')
            for rr_page in paginator_rr.paginate(HostedZoneId=zid):
                for rr in rr_page['ResourceRecordSets']:
                    if rr.get('Type') == 'A':
                        name = rr['Name'].rstrip('.')
                        vals = [r['Value'] for r in rr.get('ResourceRecords', [])]
                        records.append({
                            'AccountId': account_id,
                            'ZoneName': zname,
                            'ZoneId': zid,
                            'RecordName': name,
                            'Values': ";".join(vals)
                        })
    return records


def save_to_csv(records, filename='route53_a_records.csv'):
    """Save list of Route53 A record entries to CSV."""
    if not records:
        print("[!] No A records found to write.")
        return
    fieldnames = ['AccountId', 'ZoneName', 'ZoneId', 'RecordName', 'Values']
    try:
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        print(f"[+] Wrote {len(records)} A record entries to {filename}")
    except Exception as e:
        print(f"Error writing {filename}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    out_file = f'route53_a_records_{today}.csv'
    all_records = []

    for acct in ACCOUNTS:
        acct_id = acct['id']
        role = acct['role']
        try:
            sess = get_session(acct_id, role)
        except Exception as e:
            print(f"Failed to assume role for {acct_id}: {e}", file=sys.stderr)
            continue

        recs = fetch_a_records(sess, acct_id)
        all_records.extend(recs)

    save_to_csv(all_records, out_file)


if __name__ == '__main__':
    main()
