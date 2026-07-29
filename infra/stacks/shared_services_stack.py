from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
)
from constructs import Construct


class SharedServicesStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_name: str,
        vpc: ec2.Vpc,
        alb: elbv2.ApplicationLoadBalancer,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            cluster_name=f"{env_name}-kiwi-cluster",
            vpc=vpc,
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
        CfnOutput(
            self,
            "ListenerArn",
            value=self.listener.listener_arn,
            description="Shared ALB listener ARN — service stacks attach path-based routing rules to this",
        )
