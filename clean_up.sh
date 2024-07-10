#!/bin/bash

AWS_REGION="us-east-1"   # Replace with your desired region
VPC_ID=""   # Replace with your VPC ID
MAIN_STACK_NAME="WeatherAppStack"  # Replace with the actual main stack name
CDK_TOOLKIT_STACK_NAME="CDKToolkit"

# Function to delete an EKS cluster
delete_eks_cluster() {
    local cluster_name="$1"
    echo "Deleting EKS cluster: $cluster_name"
    if aws eks delete-cluster --name "$cluster_name" --region "$AWS_REGION"; then
        while true; do
            cluster_status=$(aws eks describe-cluster --name "$cluster_name" --region "$AWS_REGION" --query "cluster.status" --output text)
            if [[ "$cluster_status" == *"ResourceNotFoundException"* ]]; then
                echo "Cluster $cluster_name does not exist or has already been deleted."
                break
            elif [ "$cluster_status" == "DELETED" ]; then
                echo "Cluster deleted: $cluster_name"
                break
            else
                echo "Waiting for EKS cluster $cluster_name to be deleted (current status: $cluster_status)..."
                sleep 10
            fi
        done
    else
        echo "Failed to initiate EKS cluster deletion: $cluster_name"
    fi
}

# Function to delete Lambda functions
delete_lambda_functions() {
    echo "Deleting Lambda functions with associated ENIs..."
    lambda_functions=$(aws lambda list-functions --region "$AWS_REGION" --query "Functions[?starts_with(FunctionName, 'AwsCdkPractiseStack-awscdkawseksKu-Handler')].FunctionName" --output text)
    for lambda_function in $lambda_functions; do
        echo "Deleting Lambda function: $lambda_function"
        aws lambda delete-function --function-name "$lambda_function" --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "Lambda function deleted: $lambda_function"
        else
            echo "Failed to delete Lambda function: $lambda_function"
            exit 1
        fi
    done
}

# Function to delete NAT gateways
delete_nat_gateways() {
    echo "Deleting NAT gateways..."
    nat_gateways=$(aws ec2 describe-nat-gateways --region "$AWS_REGION" --query "NatGateways[?VpcId=='$VPC_ID'].NatGatewayId" --output text)
    for nat_gateway in $nat_gateways; do
        echo "Deleting NAT gateway: $nat_gateway"
        aws ec2 delete-nat-gateway --nat-gateway-id "$nat_gateway" --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "NAT gateway deleted: $nat_gateway"
        else
            echo "Failed to delete NAT gateway: $nat_gateway"
            exit 1
        fi
    done

    # Wait for NAT gateways to be deleted
    for nat_gateway in $nat_gateways; do
        echo "Waiting for NAT gateway $nat_gateway to be deleted..."
        aws ec2 wait nat-gateway-deleted --nat-gateway-ids "$nat_gateway" --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "NAT gateway deleted: $nat_gateway"
        else
            echo "Failed to delete NAT gateway: $nat_gateway"
            exit 1
        fi
    done
}

# Function to terminate and delete instances
terminate_instances() {
    echo "Terminating instances..."
    instances=$(aws ec2 describe-instances --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" --query "Reservations[*].Instances[*].InstanceId" --output text)
    for instance in $instances; do
        echo "Terminating instance: $instance"
        aws ec2 terminate-instances --instance-ids "$instance" --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "Instance terminated: $instance"
        else
            echo "Failed to terminate instance: $instance"
            continue
        fi
    done

    # Wait for instances to terminate
    for instance in $instances; do
        echo "Waiting for instance $instance to terminate..."
        aws ec2 wait instance-terminated --instance-ids "$instance" --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "Instance terminated: $instance"
        else
            echo "Failed to terminate instance: $instance"
            continue
        fi
    done
}

# Function to delete the VPC
delete_vpc() {
    echo "Deleting VPC: $VPC_ID"
    aws ec2 delete-vpc --vpc-id "$VPC_ID" --region "$AWS_REGION"
    if [ $? -eq 0 ]; then
        echo "VPC deleted: $VPC_ID"
    else
        echo "Failed to delete VPC: $VPC_ID"
        exit 1
    fi
}

# Function to delete a CloudFormation stack 
delete_stack() {
    local stack_name="$1"
    echo "Deleting stack: $stack_name"
    if aws cloudformation delete-stack --stack-name "$stack_name" --region "$AWS_REGION"; then
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$AWS_REGION"
        if [ $? -eq 0 ]; then
            echo "Stack deleted: $stack_name"
        else
            echo "Failed to delete stack: $stack_name"
            exit 1
        fi
    else
        echo "Failed to initiate stack deletion: $stack_name"
        exit 1
    fi
}


delete_eks_cluster "weather-app-cluster"

# Get a list of all stacks
stack_list=$(aws cloudformation list-stacks --region "$AWS_REGION" --query "StackSummaries[?StackStatus!='DELETE_COMPLETE'].StackName" --output text | tr '\t' '\n')

echo "Stack list:"
echo "$stack_list"

# Delete nested stacks
echo "$stack_list" | while IFS= read -r stack_name; do
    if [[ "$stack_name" == *"Nested"* ]]; then
        delete_stack "$stack_name"
    fi
done


delete_lambda_functions
delete_nat_gateways
terminate_instances
delete_vpc

delete_stack "$MAIN_STACK_NAME"
delete_stack "$CDK_TOOLKIT_STACK_NAME"

echo "All resources deleted successfully."