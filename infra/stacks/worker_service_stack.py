from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    CfnOutput,
)
from constructs import Construct

from ._fargate_service import KiwiFargateWorkerService


class WorkerServiceStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        cluster: ecs.Cluster,
        security_group: ec2.SecurityGroup,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.worker_service = KiwiFargateWorkerService(
            self,
            "Worker",
            cluster=cluster,
            security_group=security_group,
            image_asset_dir="../backend",
            dockerfile="services/worker/Dockerfile",
            command_health_check=[
                "CMD-SHELL",
                "pgrep -f 'python -m worker_app.worker' || exit 1",
            ],
            env_name=env_name,
        )

        CfnOutput(
            self,
            "WorkerServiceName",
            value=self.worker_service.service.service_name,
            description="Worker ECS service name",
        )
