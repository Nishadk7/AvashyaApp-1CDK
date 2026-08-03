import os
from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

class ComputeStack(Stack):
    """
    Compute & Load Balancing Stack: Provisions External & Internal Load Balancers,
    CloudWatch Log Groups, Launch Templates, Auto Scaling Groups with Target Tracking Policies,
    and UserData boot scripts loaded from external script files.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        external_alb_sg: ec2.ISecurityGroup,
        web_tier_sg: ec2.ISecurityGroup,
        internal_alb_sg: ec2.ISecurityGroup,
        app_tier_sg: ec2.ISecurityGroup,
        web_tier_role: iam.IRole,
        app_tier_role: iam.IRole,
        rds_endpoint: str,
        s3_bucket_name: str,
        db_password: str = "AvashyaPass2026!",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----------------------------------------------------------------------
        # 1. CloudWatch Log Groups
        # ----------------------------------------------------------------------
        # ----------------------------------------------------------------------
        # 1. CloudWatch Log Groups
        # ----------------------------------------------------------------------
        self.app_log_group = logs.LogGroup(
            self,
            "AppTierLogGroup",
            log_group_name="/aws/ec2/NishadInternsip-AvashyaApp/AppTier",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.web_log_group = logs.LogGroup(
            self,
            "WebTierLogGroup",
            log_group_name="/aws/ec2/NishadInternsip-AvashyaApp/WebTier",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.nginx_access_log_group = logs.LogGroup(
            self,
            "NginxAccessLogGroup",
            log_group_name="/aws/ec2/NishadInternsip-AvashyaApp/NginxAccess",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ----------------------------------------------------------------------
        # 2. Internal Application Load Balancer (Private App Subnets)
        # ----------------------------------------------------------------------
        self.internal_alb = elbv2.ApplicationLoadBalancer(
            self,
            "InternalALB",
            load_balancer_name="nishadinternsip-internal-alb",
            vpc=vpc,
            internet_facing=False,
            security_group=internal_alb_sg,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        self.internal_listener = self.internal_alb.add_listener(
            "InternalListener",
            port=8000,
            open=False,
        )

        # ----------------------------------------------------------------------
        # 3. External Application Load Balancer (Public Subnets)
        # ----------------------------------------------------------------------
        self.external_alb = elbv2.ApplicationLoadBalancer(
            self,
            "ExternalALB",
            load_balancer_name="nishadinternsip-external-alb",
            vpc=vpc,
            internet_facing=True,
            security_group=external_alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        self.external_listener = self.external_alb.add_listener(
            "ExternalListener",
            port=80,
            open=True,
        )

        # ----------------------------------------------------------------------
        # 3b. Public Network Load Balancer (Public Subnets -> External ALB)
        # ----------------------------------------------------------------------
        from aws_cdk import aws_elasticloadbalancingv2_targets as targets_v2

        self.public_nlb = elbv2.NetworkLoadBalancer(
            self,
            "PublicNLB",
            load_balancer_name="nishadinternsip-public-nlb",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        self.nlb_listener = self.public_nlb.add_listener(
            "NLBListener",
            port=80,
        )

        self.nlb_listener.add_targets(
            "ALBTargetGroup",
            port=80,
            targets=[targets_v2.AlbListenerTarget(self.external_listener)],
            health_check=elbv2.HealthCheck(
                protocol=elbv2.Protocol.HTTP,
                path="/",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
            ),
        )

        # ----------------------------------------------------------------------
        # 4. UserData Scripts (Loaded from external files in scripts/ directory)
        # ----------------------------------------------------------------------
        scripts_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "scripts")
        )

        # Read Web Tier UserData script & inject dynamic Internal ALB DNS
        web_script_path = os.path.join(scripts_dir, "userdata_web.sh")
        with open(web_script_path, "r", encoding="utf-8") as f:
            web_user_data_template = f.read()

        web_user_data_script = web_user_data_template.replace(
            "${INTERNAL_ALB_DNS}", self.internal_alb.load_balancer_dns_name
        )

        # Read App Tier UserData script & inject dynamic RDS, S3, & Region vars
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
        # 5. Launch Templates
        # ----------------------------------------------------------------------
        web_launch_template = ec2.LaunchTemplate(
            self,
            "AvashyaWebLT",
            launch_template_name="nishadinternsip-avashya-web-lt",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            security_group=web_tier_sg,
            role=web_tier_role,
            user_data=ec2.UserData.custom(web_user_data_script),
        )

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
        # 6. Auto Scaling Groups
        # ----------------------------------------------------------------------

        # Web Tier ASG (Public Subnets)
        self.web_asg = autoscaling.AutoScalingGroup(
            self,
            "WebTierASG",
            auto_scaling_group_name="NishadInternsip-Web-Tier-ASG",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            launch_template=web_launch_template,
            min_capacity=1,
            desired_capacity=1,
            max_capacity=3,
            health_check=autoscaling.HealthCheck.elb(grace=Duration.seconds(300)),
        )

        # App Tier ASG (Private App Subnets)
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

        # Target Tracking Scaling Policies (CPU > 70%)
        self.web_asg.scale_on_cpu_utilization(
            "WebASGScaleOnCPU",
            target_utilization_percent=70,
            cooldown=Duration.seconds(100),
            estimated_instance_warmup=Duration.seconds(100),
        )

        self.app_asg.scale_on_cpu_utilization(
            "AppASGScaleOnCPU",
            target_utilization_percent=70,
            cooldown=Duration.seconds(100),
            estimated_instance_warmup=Duration.seconds(100),
        )

        # ----------------------------------------------------------------------
        # 7. Register ASGs to ALB Target Groups
        # ----------------------------------------------------------------------

        # Web ASG registered to External ALB
        self.external_listener.add_targets(
            "WebTierTargets",
            port=80,
            targets=[self.web_asg],
            health_check=elbv2.HealthCheck(
                path="/",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
            ),
        )

        # App ASG registered to Internal ALB
        self.internal_listener.add_targets(
            "AppTierTargets",
            port=8000,
            targets=[self.app_asg],
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
            ),
        )
