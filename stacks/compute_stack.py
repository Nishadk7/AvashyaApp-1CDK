import os
from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from constructs import Construct


class ComputeStack(Stack):
    """
    Compute & CDN Stack:
    - S3 + CloudFront Distribution for Web Tier (Static Assets) & API Routing
    - Single Application Load Balancer (ALB) for App Tier API
    - App Tier Launch Template and Auto Scaling Group (EC2 in Private Subnets)
    - CloudWatch Log Group for App Tier logs
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        alb_sg: ec2.ISecurityGroup,
        app_tier_sg: ec2.ISecurityGroup,
        app_tier_role: iam.IRole,
        web_frontend_bucket: s3.IBucket,
        rds_endpoint: str,
        s3_bucket_name: str,
        db_password: str = "AvashyaPass2026!",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----------------------------------------------------------------------
        # 1. CloudWatch Log Group (App Tier Only - Nginx and Web EC2 removed)
        # ----------------------------------------------------------------------
        self.app_log_group = logs.LogGroup(
            self,
            "AppTierLogGroup",
            log_group_name="/aws/ec2/NishadInternsip-AvashyaApp/AppTier",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ----------------------------------------------------------------------
        # 2. Private Application Load Balancer (Private Subnets with Egress)
        # ----------------------------------------------------------------------
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            load_balancer_name="nishadinternsip-alb",
            vpc=vpc,
            internet_facing=False,
            security_group=alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        self.alb_listener = self.alb.add_listener(
            "ALBListener",
            port=80,
            open=True,
        )

        # ----------------------------------------------------------------------
        # 3. UserData Script for App Tier (Loaded from scripts/userdata_app.sh)
        # ----------------------------------------------------------------------
        scripts_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "scripts")
        )

        app_script_path = os.path.join(scripts_dir, "userdata_app.sh")
        with open(app_script_path, "r", encoding="utf-8") as f:
            app_user_data_template = f.read()

        app_user_data_script = (
            app_user_data_template.replace("${RDS_ENDPOINT}", rds_endpoint)
            .replace("${S3_BUCKET_NAME}", s3_bucket_name)
            .replace("${AWS_REGION}", self.region)
            .replace("${DBPASSWORD}", db_password)
        )

        # ----------------------------------------------------------------------
        # 4. App Tier Launch Template (Private Subnets)
        # ----------------------------------------------------------------------
        app_launch_template = ec2.LaunchTemplate(
            self,
            "AvashyaAppLT",
            launch_template_name="nishadinternsip-avashya-app-lt",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            security_group=app_tier_sg,
            role=app_tier_role,
            user_data=ec2.UserData.custom(app_user_data_script),
        )

        # ----------------------------------------------------------------------
        # 5. App Tier Auto Scaling Group (Private Subnets with Egress)
        # ----------------------------------------------------------------------
        self.app_asg = autoscaling.AutoScalingGroup(
            self,
            "AppTierASG",
            auto_scaling_group_name="NishadInternsip-App-Tier-ASG",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            launch_template=app_launch_template,
            min_capacity=1,
            desired_capacity=1,
            max_capacity=3,
            health_check=autoscaling.HealthCheck.elb(grace=Duration.seconds(300)),
        )

        self.app_asg.scale_on_cpu_utilization(
            "AppASGScaleOnCPU",
            target_utilization_percent=70,
            cooldown=Duration.seconds(100),
            estimated_instance_warmup=Duration.seconds(100),
        )

        # Register App ASG with Single ALB
        self.alb_listener.add_targets(
            "AppTierTargets",
            port=8000,
            targets=[self.app_asg],
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
            ),
        )

        # ----------------------------------------------------------------------
        # 6. Amazon CloudFront Distribution (Unified Web S3 + App ALB API)
        # ----------------------------------------------------------------------
        # Create CloudFront Origin Access Control (OAC)
        self.oac = cloudfront.CfnOriginAccessControl(
            self,
            "AvashyaWebFrontendOAC",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="nishadinternsip-avashya-web-oac",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4",
                description="OAC for Avashya Web Frontend S3 Bucket",
            ),
        )

        s3_origin = origins.S3BucketOrigin(web_frontend_bucket)
        alb_vpc_origin = origins.VpcOrigin.with_application_load_balancer(
            self.alb,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
            vpc_origin_name="nishadinternsip-avashya-private-alb-vpc-origin",
        )

        self.distribution = cloudfront.Distribution(
            self,
            "AvashyaCloudFrontDist",
            comment="CloudFront Distribution for Avashya Web Tier (S3) & Private App Tier (VPC Origin ALB)",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=alb_vpc_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                )
            },
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # Attach OAC to CloudFront Distribution S3 Origin
        cfn_dist = self.distribution.node.default_child
        cfn_dist.add_property_override(
            "DistributionConfig.Origins.0.OriginAccessControlId",
            self.oac.attr_id,
        )
        cfn_dist.add_property_override(
            "DistributionConfig.Origins.0.S3OriginConfig.OriginAccessIdentity",
            "",
        )

        # ----------------------------------------------------------------------
        # 7. S3 Bucket Deployment (Automated Upload of Frontend HTML/JS Assets)
        # ----------------------------------------------------------------------
        frontend_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "AvashyaApp#1", "frontend")
        )
        if os.path.exists(frontend_dir):
            s3deploy.BucketDeployment(
                self,
                "DeployWebFrontendAssets",
                sources=[s3deploy.Source.asset(frontend_dir)],
                destination_bucket=web_frontend_bucket,
                distribution=self.distribution,
                distribution_paths=["/*"],
            )

        # Outputs
        CfnOutput(
            self,
            "CloudFrontURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="Public URL for Avashya App (Free CloudFront HTTPS Domain)",
        )
        CfnOutput(
            self,
            "ALBDNSName",
            value=self.alb.load_balancer_dns_name,
            description="DNS Name of the Single Application Load Balancer",
        )

