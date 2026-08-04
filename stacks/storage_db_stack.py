from aws_cdk import RemovalPolicy, SecretValue, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_rds as rds
from aws_cdk import aws_s3 as s3
from constructs import Construct

class StorageDbStack(Stack):
    """
    Storage & Database Stack: Provisions the 100% private S3 Bucket
    (avashya-drop-uploads-2026) and a Multi-AZ Amazon RDS PostgreSQL instance
    with static credentials and public access.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        rds_sg: ec2.ISecurityGroup,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----------------------------------------------------------------------
        # 1. Object Storage: S3 Buckets (100% Private Access)
        # ----------------------------------------------------------------------
        # File Drop Uploads Bucket
        self.s3_bucket = s3.Bucket(
            self,
            "AvashyaDropUploadsBucketV2",
            bucket_name="nishadinternsip-avashya-drop-uploads-2026-v2",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Web Tier Static Frontend Bucket (Served via CloudFront)
        self.web_frontend_bucket = s3.Bucket(
            self,
            "AvashyaWebFrontendBucketV2",
            bucket_name="nishadinternsip-avashya-web-frontend-2026-v2",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Explicitly allow CloudFront Service Principal to read static web assets via OAC
        self.web_frontend_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontServicePrincipalReadOnly",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[self.web_frontend_bucket.arn_for_objects("*")],
                conditions={
                    "StringLike": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/*"
                    }
                },
            )
        )

        # ----------------------------------------------------------------------
        # 2. Data Tier: Amazon RDS PostgreSQL (Single-AZ for fast testing)
        # ----------------------------------------------------------------------
        self.db_instance = rds.DatabaseInstance(
            self,
            "AvashyaPostgresDB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            publicly_accessible=False,
            security_groups=[rds_sg],
            multi_az=False,
            allocated_storage=20,
            max_allocated_storage=100,
            database_name="avashyadadb",
            credentials=rds.Credentials.from_password(
                username="postgres",
                password=SecretValue.unsafe_plain_text("AvashyaPass2026!"),
            ),
            iam_authentication=True,
            removal_policy=RemovalPolicy.DESTROY,
            delete_automated_backups=True,
        )

