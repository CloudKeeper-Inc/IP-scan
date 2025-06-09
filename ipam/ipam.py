import boto3
import csv
import datetime
import logging
from botocore.exceptions import ClientError
from config.config import ACCOUNTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def assume_role(account_id: str, role_name: str) -> dict:
    """
    Assume the given IAM role in the specified account.
    Returns temporary security credentials.
    """
    sts = boto3.client('sts')
    response = sts.assume_role(
        RoleArn=f'arn:aws:iam::{account_id}:role/{role_name}',
        RoleSessionName=f'SessionFor_{account_id}'
    )
    return response['Credentials']


def get_session(account_id: str, role_name: str) -> boto3.Session:
    """
    Create a new boto3 Session using assumed-role credentials.
    """
    creds = assume_role(account_id, role_name)
    return boto3.Session(
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )


def fetch_public_ipv4_addresses_global(
    session: boto3.Session,
    account_id: str,
    ipam_discovery_region: str
) -> list[dict]:
    """
    Fetch all discovered public IPv4 addresses via IPAM for all regions.
    """
    ec2 = session.client('ec2')
    regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]

    ipam = session.client('ec2', region_name=ipam_discovery_region)
    discoveries = ipam.describe_ipam_resource_discoveries().get(
        "IpamResourceDiscoveries", []
    )


    data = []
    for discovery in discoveries:
        discovery_id = discovery["IpamResourceDiscoveryId"]

        for region in regions:
            next_token = None

            while True:
                params = {
                    'IpamResourceDiscoveryId': discovery_id,
                    'AddressRegion': region,
                    'MaxResults': 1000
                }
                if next_token:
                    params['NextToken'] = next_token

                try:
                    resp = ipam.get_ipam_discovered_public_addresses(**params)
                except ClientError as e:
                    break

                addresses = resp.get("IpamDiscoveredPublicAddresses", [])
                for addr in addresses:
                    sg_names = []
                    for sg in addr.get("SecurityGroups", []):
                        name = sg.get("GroupName")
                        gid = sg.get("GroupId", "")
                        sg_names.append(
                            f"{name} ({gid})" if name else gid
                        )

                    sample_time = addr.get("SampleTime")
                    if isinstance(sample_time, datetime.datetime):
                        sample_time = sample_time.isoformat()

                    data.append({
                        "AccountId": account_id,
                        "DiscoveryId": discovery_id,
                        "Region": region,
                        "IpAddress": addr.get("Address", ""),
                        "Associated": addr.get("AssociationStatus", ""),
                        "AddressType": addr.get("AddressType", ""),
                        "Service": addr.get("Service", ""),
                        "AllocationId": addr.get("AddressAllocationId", ""),
                        "VpcId": addr.get("VpcId", ""),
                        "SubnetId": addr.get("SubnetId", ""),
                        "NetworkInterfaceId": addr.get("NetworkInterfaceId", ""),
                        "SecurityGroups": ', '.join(sg_names),
                        "PublicIpv4Pool": addr.get("PublicIpv4PoolId", ""),
                        "OwnerId": addr.get("AddressOwnerId", ""),
                        "SampleTime": sample_time or ""
                    })

                next_token = resp.get("NextToken")
                if not next_token:
                    break

    return data


def main():
    today       = datetime.datetime.now().strftime('%Y-%m-%d')
    output_file = f'global_public_ipv4_{today}.csv'
    all_data    = []

    for acct in ACCOUNTS:
        acct_id     = acct['id']
        role        = acct['role']
        ipam_region = acct.get('ipam_region')

        try:
            sess = get_session(acct_id, role)
        except Exception as e:
            logger.error(f"Failed to assume role for {acct_id}: {e}")
            continue

        data = fetch_public_ipv4_addresses_global(sess, acct_id, ipam_region)
        all_data.extend(data)

    fieldnames = list(all_data[0].keys()) if all_data else []
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)

    logger.info(f"Exported {len(all_data)} records to {output_file}")


if __name__ == '__main__':
    main()
