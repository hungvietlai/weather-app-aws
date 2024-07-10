# Weather-app with CLoud Formation/AWS CDK on AWS

This repository contains the source code and necessary configurations for a weather app, an application developed in JavaScript, to be hosted on AWS using an EKS cluster.
---

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Cleanup](#cleanup)
- [License](#license)
- [Image](#image)

---

## Architecture

```plaintext
weather-app
│
├── aws_cleanup.py
├── clean_up.sh
├── Dockerfile
├── index.html
├── index.js
├── README.md
├── styles.css
├── weather_app_stack.py
├── weather-app.yaml
│
├── images
│   ├── weather-app.png
│   └── WeatherAppVPC-designer.png
│
└── weather-app-chart
    ├── Chart.yaml
    ├── values.yaml
    └── templates
        ├── deployment.yaml
        └── service.yaml

```
---
## Prerequisites

- Ensure you have the following tools installed:

- AWS CLI
- eksctl
- kubectl
- helm
- awscdk (if you wish to deploy the stack using AWS CDK)

Refer to the following links for guides on "Getting started with Amazon EKS/AWS CDK":

- [Amazon EKS Getting Started Guide](https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html)

- [AWS CDK Getting Started Guide](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)

Verify your installations with the following commands:

```bash
aws --version
eksctl version
kubectl version
```
Configure the AWS CLI with your credentials:

```bash
aws configure
```
- This will prompt you to enter your AWS Access Key ID, Secret Access Key, region, and output format. You can find the relevant informations from your IAM service.

---
## Deployment

### 1. Creating EKS cluster

#### 1.1 Clone repository

```bash
git clone https://github.com/hungvietlai/weather-app-aws.git
cd weath-app-aws
```

#### 1.2 Save your current state of AWS before deployment

- Uncomment and run the "aws_cleanup.py" script.

#### 1.3 Deploy using cloudformation 

```bash
aws cloudformation create-stack --stack-name weather-app-stack --template-body file://weather-app.yaml --capabilities CAPABILITY_NAMED_IAM

```

To check if CloudFormation has deployed, you should observe the weather-app-stack in the description:

```bash
aws cloudformation describe-stacks 

``` 

#### 1.4 Optional: Deploy using AWS CDK

- Ensure you have AWS CDK installed. Copy and paste the weather_app_stack.py file inside the CDK.

- **Note**: Ensure to download the dependencies in a virtual environment to avoid polluting your dependencies.

- Bootstrap the envirioment and then deploy

```bash
cdk bootstrap
cdk deploy
```

- To ensure the stacks have been deployed, run the command below and expect four stacks (two nested stacks, one main stack, and one CDK toolkit):

```bash
aws cloudformation describe-stacks 

``` 

-**Note**: In the outputs, look for the line below:

```bash
AwsCdkPractiseStack.EksClusterConfigCommand2AE6ED67 = aws eks update-kubeconfig --name weather-app-cluster --region <Your Region> --role-arn arn:aws:iam::<Account ID>:role/AwsCdkPractiseStack-EksClusterRole30336171-nkIMpd6Jbksy

```

### 2. Configure kubectl

- Update your kubectl config to manage the EKS cluster

```bash
aws eks --region <region_code> update-kubeconfig --name <cluster_name>
```
- If you have used AWS CDK, update your kubectl config like below, and ensure to edit the IAM role to allow your user to assume the role:

```bash

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com",
        "AWS": "arn:aws:iam::906734544038:user/hunglai"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}

```

```bash
AwsCdkPractiseStack.EksClusterConfigCommand2AE6ED67 = aws eks update-kubeconfig --name weather-app-cluster --region <Your Region> --role-arn arn:aws:iam::<Account ID>:role/AwsCdkPractiseStack-EksClusterRole30336171-nkIMpd6Jbksy

```

#### 2.1 Verify your nodes:

```bash
kubectl get nodes
```
- There should be 3 nodes listed.

### 3.Deploy the Weather App:

```bash
helm install weather-app-chart weather-app-charts/
```
#### 3.1 Check deployments, services:

```bash
kubectl get deploy,svc
```
- You should observe 2 deployments and 2 services.

### 4. Access the app:

- Access the weather-app app via LoadBalancer public IP

- **Note**: If you can't access the app, review the security settings of the LB in the EC2 dashboard. Ensure inbound rules allow traffic on ports 80.

## Cleanup:

- When done testing, to avoid unnecessary costs, delete the cluster:

- if you have deployed using cloudformation

```bash
helm uninstall weather-app
aws cloudformation describe-stacks --stack-name weather-app-stack
```
- If you have deployed using AWS CDK:

```bash
cdk destroy
```

- **Note** If you encounter any errors running cdk destroy, execute the shell script "clean_up.sh":

```bash
# Change file permission
chmod +x clean_up.sh
./clean_up.sh
```

- Alternateively, you can also delete resources from AWS console

- **Note**: Rerun aws_cleanup.py to ensure you have no other resources remaining.

## License 

This project is licensed under the MIT License. For the full text of the license, see the LICENSE file.

## Image

![infra-image](https://github.com/hungvietlai/weather-app-aws/blob/master/images/WeatherAppVPC-designer.png)
![weather-app](https://github.com/hungvietlai/weather-app-aws/blob/master/images/weather-app.png)