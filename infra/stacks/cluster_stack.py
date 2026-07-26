from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    CfnOutput,
)
from constructs import Construct


class ClusterStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        vpc: ec2.Vpc,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            cluster_name=f"{env_name}-kiwi-cluster",
            vpc=vpc,
        )

        CfnOutput(
            self,
            "ClusterName",
            value=self.cluster.cluster_name,
            description="ECS cluster name",
        )
        CfnOutput(
            self,
            "ClusterArn",
            value=self.cluster.cluster_arn,
            description="ECS cluster ARN",
        )
