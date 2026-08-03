from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct

class SecurityStack(Stack):
    """
    Security Stack: Provisions granular IAM Roles from scratch and
    implements strict least-privilege Security Group chaining for the 3-tier architecture.
    """

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----------------------------------------------------------------------
        # 1. IAM Roles (Built From Scratch)
        # ----------------------------------------------------------------------

        # Web Tier IAM Role
        self.web_tier_role = iam.Role(
            self,
            "AvashyaEC2WebRole",
            role_name="NishadInternsip-Avashya-EC2-Web-Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
            description="IAM Role for Web Tier EC2 instances with CloudWatch Agent capabilities.",
        )

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
        # 2. Security Groups Chaining (Built From Scratch)
        # ----------------------------------------------------------------------

        # 1. External-ALB-SG: Inbound 80 & 443 from 0.0.0.0/0
        self.external_alb_sg = ec2.SecurityGroup(
            self,
            "ExternalALBSG",
            vpc=vpc,
            security_group_name="NishadInternsip-External-ALB-SG",
            description="External Internet-Facing Load Balancer Security Group",
            allow_all_outbound=True,
        )
        self.external_alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP 80 traffic from Internet",
        )
        self.external_alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS 443 traffic from Internet",
        )

        # 2. Web-Tier-SG: Inbound HTTP (80/5000) ONLY from External-ALB-SG
        self.web_tier_sg = ec2.SecurityGroup(
            self,
            "WebTierSG",
            vpc=vpc,
            security_group_name="NishadInternsip-Web-Tier-SG",
            description="Web Tier Security Group",
            allow_all_outbound=True,
        )
        self.web_tier_sg.add_ingress_rule(
            self.external_alb_sg,
            ec2.Port.tcp(80),
            "Allow HTTP 80 ONLY from External-ALB-SG",
        )
        self.web_tier_sg.add_ingress_rule(
            self.external_alb_sg,
            ec2.Port.tcp(5000),
            "Allow HTTP 5000 ONLY from External-ALB-SG",
        )

        # 3. Internal-ALB-SG: Inbound HTTP (8000) ONLY from Web-Tier-SG
        self.internal_alb_sg = ec2.SecurityGroup(
            self,
            "InternalALBSG",
            vpc=vpc,
            security_group_name="NishadInternsip-Internal-ALB-SG",
            description="Internal Application Load Balancer Security Group",
            allow_all_outbound=True,
        )
        self.internal_alb_sg.add_ingress_rule(
            self.web_tier_sg,
            ec2.Port.tcp(8000),
            "Allow TCP 8000 ONLY from Web-Tier-SG",
        )

        # 4. App-Tier-SG: Inbound TCP (8000) ONLY from Internal-ALB-SG
        self.app_tier_sg = ec2.SecurityGroup(
            self,
            "AppTierSG",
            vpc=vpc,
            security_group_name="NishadInternsip-App-Tier-SG",
            description="App Tier Security Group",
            allow_all_outbound=True,
        )
        self.app_tier_sg.add_ingress_rule(
            self.internal_alb_sg,
            ec2.Port.tcp(8000),
            "Allow TCP 8000 ONLY from Internal-ALB-SG",
        )

        # 5. RDS-Database-SG: Inbound PostgreSQL (5432) ONLY from App-Tier-SG
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
