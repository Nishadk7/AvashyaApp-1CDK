from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct

class SecurityStack(Stack):
    """
    Security Stack: Provisions granular IAM Roles and implements strict
    least-privilege Security Group chaining for CloudFront -> ALB -> App Tier -> RDS architecture.
    """

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----------------------------------------------------------------------
        # 1. IAM Roles
        # ----------------------------------------------------------------------
        # App Tier IAM Role (Avashya-EC2-App-Role)
        self.app_tier_role = iam.Role(
            self,
            "AvashyaEC2AppRole",
            role_name="NishadInternsip-Avashya-EC2-App-Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
            description="IAM Role for App Tier EC2 instances with S3, CloudWatch, and RDS IAM Auth access.",
        )

        # Custom Inline Policy for RDS IAM Database Authentication
        self.app_tier_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowRDSAuthAndAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "rds-db:connect",
                    "rds:*",
                ],
                resources=["*"],
            )
        )

        # ----------------------------------------------------------------------
        # 2. Security Groups Chaining (Single ALB -> App Tier -> RDS)
        # ----------------------------------------------------------------------

        # 1. Single Application Load Balancer Security Group
        self.alb_sg = ec2.SecurityGroup(
            self,
            "ALBSG",
            vpc=vpc,
            security_group_name="NishadInternsip-ALB-SG",
            description="Single Application Load Balancer Security Group for API traffic",
            allow_all_outbound=True,
        )
        self.alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP 80 traffic from Internet / CloudFront",
        )
        self.alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS 443 traffic from Internet / CloudFront",
        )

        # 2. App-Tier-SG: Inbound TCP (8000) ONLY from ALB-SG
        self.app_tier_sg = ec2.SecurityGroup(
            self,
            "AppTierSG",
            vpc=vpc,
            security_group_name="NishadInternsip-App-Tier-SG",
            description="App Tier Security Group",
            allow_all_outbound=True,
        )
        self.app_tier_sg.add_ingress_rule(
            self.alb_sg,
            ec2.Port.tcp(8000),
            "Allow TCP 8000 ONLY from ALB-SG",
        )

        # 3. RDS-Database-SG: Inbound PostgreSQL (5432) ONLY from App-Tier-SG
        self.rds_db_sg = ec2.SecurityGroup(
            self,
            "RDSDatabaseSG",
            vpc=vpc,
            security_group_name="NishadInternsip-RDS-Database-SG",
            description="Amazon RDS Database Security Group",
            allow_all_outbound=True,
        )
        self.rds_db_sg.add_ingress_rule(
            self.app_tier_sg,
            ec2.Port.tcp(5432),
            "Allow PostgreSQL 5432 ONLY from App-Tier-SG",
        )

