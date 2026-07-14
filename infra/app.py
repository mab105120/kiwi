import aws_cdk as cdk
from stacks import NetworkStack, DataStack

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

app.synth()
