from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_eks as eks,
    CfnOutput,
    Tags

)
from constructs import Construct
from aws_cdk.lambda_layer_kubectl_v28 import KubectlV28Layer

class WeatherAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster_name = "weather-app-cluster"
        kubectl_layer = KubectlV28Layer(self, "KubectlLayer")

        vpc = ec2.Vpc(self, "WeatherAppVPC",
                      ip_addresses=ec2.IpAddresses.cidr("192.168.0.0/16"),
                      max_azs=2,
                      enable_dns_support=True,
                      enable_dns_hostnames=True, 
                      subnet_configuration=[
                          ec2.SubnetConfiguration(
                              name="Public",
                              subnet_type=ec2.SubnetType.PUBLIC,
                              cidr_mask=24,
                              map_public_ip_on_launch=True
                          ),
                          ec2.SubnetConfiguration(
                              name="Private",
                              subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                              cidr_mask=24
                          )
                      ])

        for i, subnet in enumerate(vpc.public_subnets):
            Tags.of(subnet).add("Name", f"my_public_subnet{i+1}")
            Tags.of(subnet).add(f"kubernetes.io/cluster/{cluster_name}", "shared")
            Tags.of(subnet).add("kubernetes.io/role/elb", "1")

        for i, subnet in enumerate(vpc.private_subnets):
            Tags.of(subnet).add("Name", f"my_private_subnet{i+1}")
            Tags.of(subnet).add(f"kubernetes.io/cluster/{cluster_name}", "shared")

        nat_epi1 = ec2.CfnEIP(self, "NatEIP1", domain="vpc")
        nat_epi2 = ec2.CfnEIP(self, "NatEIP2", domain="vpc")

        nat_gw1 = ec2.CfnNatGateway(self, "Natgateway1",
                                    subnet_id=vpc.public_subnets[0].subnet_id,
                                    allocation_id=nat_epi1.attr_allocation_id)
        nat_gw2 = ec2.CfnNatGateway(self, "NatGateway2",
                                    subnet_id=vpc.public_subnets[1].subnet_id,
                                    allocation_id=nat_epi2.attr_allocation_id) 
        
        public_route_table = ec2.CfnRouteTable(self, "PublicRouteTable",
                                               vpc_id=vpc.vpc_id)
        
        ec2.CfnRoute(self, "PublicRoute",
                     route_table_id=public_route_table.attr_route_table_id,
                     destination_cidr_block="0.0.0.0/0",
                     gateway_id=vpc.internet_gateway_id)

        ec2.CfnSubnetRouteTableAssociation(self, "PublicSubnetRouteTableAssociation1",
                                           subnet_id=vpc.public_subnets[0].subnet_id,
                                           route_table_id=public_route_table.attr_route_table_id)
        
        ec2.CfnSubnetRouteTableAssociation(self, "PublicSubnetRouteTableAssociation2",
                                           subnet_id=vpc.public_subnets[1].subnet_id,
                                           route_table_id=public_route_table.attr_route_table_id)

        private_route_table1 = ec2.CfnRouteTable(self, "PrivateRouteTable1",
                                                 vpc_id=vpc.vpc_id)

        private_route_table2 = ec2.CfnRouteTable(self, "PrivateRouteTable2",
                                                 vpc_id=vpc.vpc_id)

        ec2.CfnRoute(self, "PrivateRoute1",
                     route_table_id=private_route_table1.attr_route_table_id,
                     destination_cidr_block="0.0.0.0/0",
                     nat_gateway_id=nat_gw1.ref)

        ec2.CfnRoute(self, "PrivateRoute2",
                     route_table_id=private_route_table2.attr_route_table_id,
                     destination_cidr_block="0.0.0.0/0",
                     nat_gateway_id=nat_gw2.ref)

        ec2.CfnSubnetRouteTableAssociation(self, "PrivateSubnetRouteTableAssociation1",
                                           subnet_id=vpc.private_subnets[0].subnet_id,
                                           route_table_id=private_route_table1.attr_route_table_id)

        ec2.CfnSubnetRouteTableAssociation(self, "PrivateSubnetRouteTableAssociation2",
                                           subnet_id=vpc.private_subnets[1].subnet_id,
                                           route_table_id=private_route_table2.attr_route_table_id)

        eks_security_group = ec2.SecurityGroup(self, "EksSecurityGroup",
                                               vpc=vpc,
                                               description="Security group for EKS cluster",
                                               allow_all_outbound=True)
        
        eks_security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP traffic")

        eks_cluster_role = iam.Role(self, "EksClusterRole",
                                    assumed_by=iam.ServicePrincipal("eks.amazonaws.com"),
                                    managed_policies=[
                                        iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSClusterPolicy"),
                                        iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSServicePolicy"),
                                        iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSVPCResourceController")             
                                    ])

        eks_worker_role = iam.Role(self, "EksWorkerRole",
                                   assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                                   managed_policies=[
                                       iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSWorkerNodePolicy"),
                                       iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKS_CNI_Policy"),
                                       iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly")
                                   ])

        iam.CfnInstanceProfile(self, "EksWorkerInstanceProfile",
                                                             roles=[eks_worker_role.role_name])

        eks_cluster = eks.Cluster(self, "EksCluster",
                                  cluster_name=cluster_name,
                                  vpc=vpc,
                                  security_group=eks_security_group,
                                  default_capacity=0,
                                  masters_role=eks_cluster_role,
                                  version=eks.KubernetesVersion.V1_28,
                                  kubectl_layer=kubectl_layer)

        eks_cluster.add_auto_scaling_group_capacity("EksNodeGroup",
                                                    instance_type=ec2.InstanceType("t2.micro"),
                                                    min_capacity=3,
                                                    max_capacity=4,
                                                    vpc_subnets=ec2.SubnetSelection(
                                                        subnets=vpc.private_subnets))

        CfnOutput(self, "ClusterEndpoint",
                  description="The endpoint for your EKS Kubernetes API.",
                  value=eks_cluster.cluster_endpoint)

        CfnOutput(self, "SubnetIds",
                  description="The IDs of the subnets used by the EKS cluster",
                  value=",".join([subnet.subnet_id for subnet in vpc.public_subnets]))

        CfnOutput(self, "SecurityGroupId",
                  description="The ID of the security group used by the EKS cluster",
                  value=eks_security_group.security_group_id)