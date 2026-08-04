from aws_cdk import Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from constructs import Construct


class Route53Stack(Stack):
    """
    Route 53 Stack: Configures AWS Route 53 Hosted Zone and Alias A-Records
    to route public DNS traffic to the CloudFront Distribution.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        distribution: cloudfront.IDistribution,
        domain_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Public Hosted Zone
        self.hosted_zone = route53.PublicHostedZone(
            self,
            "AvashyaHostedZone",
            zone_name=domain_name,
            comment="Public Hosted Zone for AvashyaApp",
        )

        # 2. Apex Alias A Record -> CloudFront
        self.apex_record = route53.ARecord(
            self,
            "ApexAliasRecord",
            zone=self.hosted_zone,
            record_name="",
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(distribution)
            ),
            comment="Apex Alias A-record routing public traffic to CloudFront Distribution",
        )

        # 3. WWW Subdomain Alias A Record -> CloudFront
        self.www_record = route53.ARecord(
            self,
            "WwwAliasRecord",
            zone=self.hosted_zone,
            record_name="www",
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(distribution)
            ),
            comment="WWW Subdomain Alias A-record routing public traffic to CloudFront Distribution",
        )
