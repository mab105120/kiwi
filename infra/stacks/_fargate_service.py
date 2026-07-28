from aws_cdk import (
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
)
from constructs import Construct


class KiwiFargateWebService(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        cluster: ecs.Cluster,
        vpc: ec2.Vpc,
        security_group: ec2.SecurityGroup,
        image_asset_dir: str,
        dockerfile: str,
        container_port: int,
        health_check_path: str,
        env_name: str,
    ):
        super().__init__(scope, id)

        log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"/ecs/{env_name}/{id}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            cpu=256,
            memory_limit_mib=512,
        )

        task_definition.add_container(
            "Container",
            image=ecs.ContainerImage.from_asset(
                directory=image_asset_dir,
                file=dockerfile,
            ),
            port_mappings=[ecs.PortMapping(container_port=container_port)],
            logging=ecs.LogDriver.aws_logs(stream_prefix=id, log_group=log_group),
        )

        self.service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            assign_public_ip=False,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )

        self.target_group = elbv2.ApplicationTargetGroup(
            self,
            "TargetGroup",
            vpc=vpc,
            port=container_port,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(path=health_check_path),
        )

        self.service.attach_to_application_target_group(self.target_group)
