"""
This script is designed to verify the cleanup of AWS services following the deletion of a CloudFormation stack. 
It helps identify any resources that were not automatically deleted, allowing for manual cleanup.
"""

import boto3
import json


def capture_state():
    services = []
    ec2 = boto3.client('ec2', region_name='us-east-1')
    eks = boto3.client('eks', region_name='us-east-1')
    iam = boto3.client('iam', region_name='us-east-1')

    vpcs = ec2.describe_vpcs()
    for vpc in vpcs['Vpcs']:
        services.append(f"VPC ID: {vpc['VpcId']} - State: {vpc['State']}")

    subnets = ec2.describe_subnets()
    for subnet in subnets['Subnets']:
        services.append(f"Subnet ID: {subnet['SubnetId']} - Availability Zone: {subnet['AvailabilityZone']}")

    nats = ec2.describe_nat_gateways()
    for nat in nats['NatGateways']:
        services.append(f"NAT Gateway ID: {nat['NatGatewayId']} - State: {nat['State']}")

    sgs = ec2.describe_security_groups()
    for sg in sgs['SecurityGroups']:
        services.append(f"SG ID: {sg['GroupId']} - Description: {sg['Description']}")

    eips = ec2.describe_addresses()
    for eip in eips['Addresses']:
        services.append(f"EIP Allocation ID: {eip['AllocationId']} - Associated with: {eip.get('InstanceId', 'Not associated')}")

    routes = ec2.describe_route_tables()
    for route_table in routes['RouteTables']:
            for association in route_table['Associations']:
                services.append(f"Route Table ID: {route_table['RouteTableId']} - Associated with Subnet: {association.get('SubnetId', 'Not associated')}")

    instances = ec2.describe_instances()
    for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                services.append(f"Instance ID: {instance['InstanceId']} - State: {instance['State']['Name']}")

    igws = ec2.describe_internet_gateways()
    for igw in igws['InternetGateways']:
        services.append(f"IGW ID: {igw['InternetGatewayId']}")

    clusters = eks.list_clusters()
    for cluster_name in clusters['clusters']:
            cluster_info = eks.describe_cluster(name=cluster_name)
            services.append(f"Cluster Name: {cluster_name} - Status: {cluster_info['cluster']['status']}")

    return services

#Saves the captured state to a JSON file for later comparison.
def save_state(file_name, state):
     with open(file_name, 'w') as f:
          json.dump(state, f)

#Loads the previously saved state from a JSON file.
def load_state(file_name):
     with open(file_name, 'r'):
          json.load(file_name)

#Compares two states and identifies differences. This helps in identifying resources that were not deleted or unexpectedly created.
def compare_state(before, after):
     return set(before) - set(after), set(after) - set(before)


# Example usage (uncomment the following lines to use):

# Capture initial state of services
# initial_state = capture_state()
# save_state('before_deployment.json', initial_state)

# Capture state after deletion of the CloudFormation stack
# post_deletion_state = capture_state()
# save_state('after_deletion.json', post_deletion_state)

# Compare initial and post-deletion states to identify any resources that were not deleted
# initial_state = load_state('before_deployment.json')
# final_state = load_state('after_deletion.json')
# resources_left_behind, newly_created_resources = compare_states(initial_state, final_state)
# print("Resources left behind:", resources_left_behind)
# print("Newly created resources (unexpected):", newly_created_resources)