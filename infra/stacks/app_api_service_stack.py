from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
)
from constructs import Construct
from ._fargate_service import KiwiFargateWebService


class AppApiServiceStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        vpc: ec2.Vpc,
        security_group: ec2.SecurityGroup,
        cluster: ecs.Cluster,
        listener: elbv2.ApplicationListener,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.app_api_service = KiwiFargateWebService(
            self,
            "AppApi",
            cluster=cluster,
            vpc=vpc,
            security_group=security_group,
            image_asset_dir="../backend",
            dockerfile="services/app-api/Dockerfile",
            container_port=8080,
            health_check_path="/app-api/healthz",
            env_name=env_name,
        )

        elbv2.ApplicationListenerRule(
            self,
            "AppApiRule",
            listener=listener,
            priority=20,
            conditions=[elbv2.ListenerCondition.path_patterns(["/app-api/*"])],
            target_groups=[self.app_api_service.target_group],
        )

        CfnOutput(
            self,
            "AppApiServiceName",
            value=self.app_api_service.service.service_name,
            description="App-api ECS service name",
        )
