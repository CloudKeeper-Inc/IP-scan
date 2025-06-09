import boto3
import csv
import datetime
import logging
import sys

from config.config import ACCOUNTS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


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


def get_all_regions(session):
    """Return all available AWS region names for the given session."""
    ec2 = session.client('ec2')
    return [r['RegionName'] for r in ec2.describe_regions()['Regions']]


def fetch_enis(session, account_id, region):
    """Fetch ENIs from the given session and region, tagging each record with the AWS account ID."""
    records = []
    ec2 = session.client('ec2', region_name=region)
    paginator = ec2.get_paginator('describe_network_interfaces')
    for page in paginator.paginate():
        for eni in page.get('NetworkInterfaces', []):
            eni_id = eni.get('NetworkInterfaceId')
            private_ips = [ip.get('PrivateIpAddress') for ip in eni.get('PrivateIpAddresses', [])]
            assoc = eni.get('Association') or {}
            public_ip = assoc.get('PublicIp', 'None')
            records.append({
                'Account': account_id,
                'Region': region,
                'ENI_ID': eni_id,
                'PrivateIPs': ";".join(private_ips),
                'PublicIPs': public_ip
            })
    return records


def save_to_csv(records, filename):
    """Save list of ENI records to a CSV file."""
    if not records:
        logger.info("No ENIs found to write.")
        return
    fieldnames = ['Account', 'Region', 'ENI_ID', 'PrivateIPs', 'PublicIPs']
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        logger.info(f"Saved {len(records)} ENI entries to {filename}")
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")
        sys.exit(1)


def main():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    csv_file = f'enis_{current_date}.csv'

    all_records = []

    for account in ACCOUNTS:
        account_id = account['id']
        role_name = account['role']
        regions = account.get('eni_regions', [])

        logger.info(f"Processing account {account_id}")
        try:
            session = get_session(account_id, role_name)
        except Exception as e:
            logger.error(f"Failed to assume role for account {account_id}: {e}")
            continue

        if not regions:
            try:
                regions = get_all_regions(session)
            except Exception as e:
                logger.error(f"Error fetching regions for account {account_id}: {e}")
                continue

        for region in regions:
            logger.info(f"Fetching ENIs for account {account_id} in region {region}")
            try:
                records = fetch_enis(session, account_id, region)
                all_records.extend(records)
            except Exception as e:
                logger.error(f"Error fetching ENIs in {region} for account {account_id}: {e}")
                continue

    save_to_csv(all_records, csv_file)


if __name__ == '__main__':
    main()
