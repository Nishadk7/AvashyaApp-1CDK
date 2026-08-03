from aws_cdk import Stack
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from constructs import Construct

class Route53Stack(Stack):
    """
    Route 53 Stack: Configures AWS Route 53 Hosted Zone and Alias A-Records
    to route public DNS traffic to the External Internet-Facing Application Load Balancer.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        target_lb: elbv2.ILoadBalancer,
        domain_name: str = "avashyaapp.com",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Public Hosted Zone
        self.hosted_zone = route53.PublicHostedZone(
            self,
            "AvashyaHostedZone",
            zone_name=domain_name,
            comment="Public Hosted Zone for AvashyaApp 3-Tier Web Application",
        )

        # 2. Apex Alias A Record (e.g. avashyaapp.com -> Public NLB)
        self.apex_record = route53.ARecord(
            self,
            "ApexAliasRecord",
            zone=self.hosted_zone,
            record_name="",
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(target_lb)
            ),
            comment="Apex Alias A-record routing public traffic to Public NLB",
        )

        # 3. WWW Subdomain Alias A Record (e.g. www.avashyaapp.com -> Public NLB)
        self.www_record = route53.ARecord(
            self,
            "WwwAliasRecord",
            zone=self.hosted_zone,
            record_name="www",
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(target_lb)
            ),
            comment="WWW Subdomain Alias A-record routing public traffic to Public NLB",
        )
