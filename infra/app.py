import aws_cdk as cdk
from stacks import (
    NetworkStack,
    DataStack,
    SharedServicesStack,
    IdentityServiceStack,
    AppApiServiceStack,
)

app = cdk.App()

env_name = app.node.try_get_context("env") or "dev"
config = app.node.try_get_context(env_name)
env_config = {"db_name": config["db_name"]}
aws_env = cdk.Environment(account=config["account"], region=config["region"])

# cicd_stack = CiCdStack(
#     app,
#     f"{env_name}-kiwi-cicd-stack",
#     env_name=env_name,
#     github_repo=config["github_repo"],
#     env=aws_env,
# )

network_stack = NetworkStack(
    app, f"{env_name}-kiwi-vpc-stack", env_name=env_name, env=aws_env
)

shared_services_stack = SharedServicesStack(
    app,
    f"{env_name}-kiwi-shared-services-stack",
    env_name=env_name,
    vpc=network_stack.vpc,
    alb=network_stack.alb,
    env=aws_env,
)

data_stack = DataStack(
    app,
    f"{env_name}-kiwi-db-stack",
    env_name,
    env_config,
    network_stack.vpc,
    network_stack.db_security_group,
    network_stack.lambda_security_group,
    env=aws_env,
)

identity_service_stack = IdentityServiceStack(
    app,
    f"{env_name}-kiwi-identity-service-stack",
    env_name=env_name,
    cluster=shared_services_stack.cluster,
    vpc=network_stack.vpc,
    security_group=network_stack.fargate_services_security_group,
    listener=shared_services_stack.listener,
    env=aws_env,
)

app_api_service_stack = AppApiServiceStack(
    app,
    f"{env_name}-kiwi-app-api-service-stack",
    env_name=env_name,
    cluster=shared_services_stack.cluster,
    vpc=network_stack.vpc,
    security_group=network_stack.fargate_services_security_group,
    listener=shared_services_stack.listener,
    env=aws_env,
)

app.synth()
