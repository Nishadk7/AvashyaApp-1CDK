from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

class VpcStack(Stack):
    """
    VPC Stack: Provisions a custom Amazon VPC across 2 Availability Zones
    with 6 subnets total (2 Public, 2 Private App, 2 Isolated Database),
    attached Internet Gateway, 2 NAT Gateways, and an S3 Gateway VPC Endpoint.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Custom Amazon VPC (10.0.0.0/16 across 2 AZs)
        self.vpc = ec2.Vpc(
            self,
            "AvashyaVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,
            nat_gateways=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="PrivateApp",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="IsolatedDB",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # 2. Free Amazon S3 Gateway VPC Endpoint attached to Private App Subnets
        self.s3_endpoint = self.vpc.add_gateway_endpoint(
            "S3GatewayEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)],
        )
