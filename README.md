# Find and Compare Route 53 A Records with IPs in your AWS Account

# IAM Policy & Role Setup

While creating the role, select the trusted entity type as "AWS account", choose "Another AWS account", and enter the account ID of the primary (main) account.
This process will be the same for every account.
Also, Make sure that the credentials of the primary account are configured in your terminal.

---

## 1. Create the Custom Policy

1. Open the AWS Console and navigate to **IAM → Policies → Create policy**.  
2. Switch to the **JSON** tab and paste this policy document:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "IPAMDiscoveryAndRegionAccess",
         "Effect": "Allow",
         "Action": [
           "ec2:DescribeRegions",
           "ec2:DescribeIpamResourceDiscoveries",
           "ec2:GetIpamDiscoveredPublicAddresses"
         ],
         "Resource": "*"
       },
       {
         "Sid": "Route53ARecordReadOnly",
         "Effect": "Allow",
         "Action": [
           "route53:ListHostedZones",
           "route53:ListResourceRecordSets"
         ],
         "Resource": "*"
       },
       {
         "Sid": "EC2NetworkInterfacesReadonly",
         "Effect": "Allow",
         "Action": [
           "ec2:DescribeNetworkInterfaces"
         ],
         "Resource": "*"
       }
     ]
   }
3. Click Next, name it IPAM-And-Route53-NetworkInterface-Readonly, add an optional description, and click Create policy.

### 2. Trust Relationship

Also, make sure the trusted relationship at the end of the page while creating the role looks like the one below, or you can also review it after the role is created:

    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::<main-account-id>:root"
          },
          "Action": "sts:AssumeRole",
          "Condition": {}
        }
      ]
    }

### 3. Configure Accounts adn Region

See [`config/config.py`](https://github.com/CloudKeeper-Inc/IP-scan/blob/main/config/config.py) for examples of how to configure your accounts and regions.

### 4. Install boto3 in your Python environment
    pip install boto3

### 5. From the root directory of this GitHub repository, simply run:
    python main.py
### 6. The results will be saved in a folder named with today’s date (e.g., 2025-06-09).

You can find all the findings in that folder.
