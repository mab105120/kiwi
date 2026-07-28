from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
)
from constructs import Construct

from ._fargate_service import KiwiFargateWebService


class IdentityServiceStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        cluster: ecs.Cluster,
        vpc: ec2.Vpc,
        security_group: ec2.SecurityGroup,
        alb: elbv2.ApplicationLoadBalancer,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.identity_service = KiwiFargateWebService(
            self,
            "Identity",
            cluster=cluster,
            vpc=vpc,
            security_group=security_group,
            image_asset_dir="../backend",
            dockerfile="services/identity/Dockerfile",
            container_port=8080,
            health_check_path="/identity/healthz",
            env_name=env_name,
        )

        self.listener = alb.add_listener(
            "HttpListener",
            port=80,
            default_action=elbv2.ListenerAction.fixed_response(
                404,
                content_type="application/json",
                message_body='{"error": "not found"}',
            ),
        )

        elbv2.ApplicationListenerRule(
            self,
            "IdentityRule",
            listener=self.listener,
            priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/identity/*"])],
            target_groups=[self.identity_service.target_group],
        )

        CfnOutput(
            self,
            "IdentityServiceName",
            value=self.identity_service.service.service_name,
            description="Identity ECS service name",
        )
