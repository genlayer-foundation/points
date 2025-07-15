#!/bin/bash
set -e

# AWS Private Network Setup for App Runner
# This script creates private subnets with NAT Gateway for proper App Runner VPC connector setup

VPC_ID="vpc-0e093eda3b7ad6db1"
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Setting up private network infrastructure for VPC: $VPC_ID"

# Step 1: Create private subnets (using 10.0.100.0/24 range for private subnets)
echo ""
echo "Step 1: Creating private subnets..."

# Create private subnet in us-east-1a
PRIVATE_SUBNET_1A=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.101.0/24 \
    --availability-zone us-east-1a \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=tally-private-1a}]" \
    --query 'Subnet.SubnetId' \
    --output text)
echo "Created private subnet in us-east-1a: $PRIVATE_SUBNET_1A"

# Create private subnet in us-east-1b
PRIVATE_SUBNET_1B=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.102.0/24 \
    --availability-zone us-east-1b \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=tally-private-1b}]" \
    --query 'Subnet.SubnetId' \
    --output text)
echo "Created private subnet in us-east-1b: $PRIVATE_SUBNET_1B"

# Create private subnet in us-east-1c
PRIVATE_SUBNET_1C=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.103.0/24 \
    --availability-zone us-east-1c \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=tally-private-1c}]" \
    --query 'Subnet.SubnetId' \
    --output text)
echo "Created private subnet in us-east-1c: $PRIVATE_SUBNET_1C"

# Step 2: Allocate Elastic IP for NAT Gateway
echo ""
echo "Step 2: Allocating Elastic IP for NAT Gateway..."
EIP_ALLOC_ID=$(aws ec2 allocate-address \
    --domain vpc \
    --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=tally-nat-eip}]" \
    --query 'AllocationId' \
    --output text)
echo "Allocated Elastic IP: $EIP_ALLOC_ID"

# Step 3: Create NAT Gateway in one of the public subnets
echo ""
echo "Step 3: Creating NAT Gateway in public subnet..."
# Using the correct public subnet (us-east-1a)
NAT_GATEWAY_ID=$(aws ec2 create-nat-gateway \
    --subnet-id subnet-0d7295c43d9d05ab6 \
    --allocation-id $EIP_ALLOC_ID \
    --tag-specifications "ResourceType=nat-gateway,Tags=[{Key=Name,Value=tally-nat-gateway}]" \
    --query 'NatGateway.NatGatewayId' \
    --output text)
echo "Created NAT Gateway: $NAT_GATEWAY_ID"

# Wait for NAT Gateway to be available
echo "Waiting for NAT Gateway to become available..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GATEWAY_ID
echo "NAT Gateway is now available"

# Step 4: Create route table for private subnets
echo ""
echo "Step 4: Creating route table for private subnets..."
PRIVATE_ROUTE_TABLE_ID=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=tally-private-routes}]" \
    --query 'RouteTable.RouteTableId' \
    --output text)
echo "Created route table: $PRIVATE_ROUTE_TABLE_ID"

# Add route to NAT Gateway
aws ec2 create-route \
    --route-table-id $PRIVATE_ROUTE_TABLE_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id $NAT_GATEWAY_ID
echo "Added route to NAT Gateway"

# Associate route table with private subnets
echo "Associating route table with private subnets..."
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_1A --route-table-id $PRIVATE_ROUTE_TABLE_ID
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_1B --route-table-id $PRIVATE_ROUTE_TABLE_ID
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_1C --route-table-id $PRIVATE_ROUTE_TABLE_ID
echo "Route table associated with all private subnets"

# Step 5: Create new VPC Connector
echo ""
echo "Step 5: Creating new VPC Connector with private subnets..."

# Create a new security group for the VPC connector
VPC_CONNECTOR_SG=$(aws ec2 create-security-group \
    --group-name apprunner-tally-private-connector \
    --description "Security group for App Runner VPC connector with private subnets" \
    --vpc-id $VPC_ID \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=apprunner-tally-private-connector}]" \
    --query 'GroupId' \
    --output text)
echo "Created security group: $VPC_CONNECTOR_SG"

# Add outbound rules for HTTPS and PostgreSQL
aws ec2 authorize-security-group-egress \
    --group-id $VPC_CONNECTOR_SG \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0
aws ec2 authorize-security-group-egress \
    --group-id $VPC_CONNECTOR_SG \
    --protocol tcp \
    --port 5432 \
    --cidr 10.0.0.0/16
echo "Added security group rules"

# Create VPC Connector
VPC_CONNECTOR_ARN=$(aws apprunner create-vpc-connector \
    --vpc-connector-name tally-private-vpc-connector \
    --subnets $PRIVATE_SUBNET_1A $PRIVATE_SUBNET_1B $PRIVATE_SUBNET_1C \
    --security-groups $VPC_CONNECTOR_SG \
    --query 'VpcConnector.VpcConnectorArn' \
    --output text)
echo "Created VPC Connector: $VPC_CONNECTOR_ARN"

# Output summary
echo ""
echo "========================================="
echo "Private Network Setup Complete!"
echo "========================================="
echo ""
echo "Created Resources:"
echo "- Private Subnets: $PRIVATE_SUBNET_1A, $PRIVATE_SUBNET_1B, $PRIVATE_SUBNET_1C"
echo "- NAT Gateway: $NAT_GATEWAY_ID"
echo "- Elastic IP: $EIP_ALLOC_ID"
echo "- Route Table: $PRIVATE_ROUTE_TABLE_ID"
echo "- Security Group: $VPC_CONNECTOR_SG"
echo "- VPC Connector: $VPC_CONNECTOR_ARN"
echo ""
echo "Next Step: Deploy your App Runner service with the new VPC connector:"
echo ""
echo "cd /Users/rasca/Dev/tally/backend"
echo "./deploy-apprunner.sh tally-backend $VPC_CONNECTOR_ARN"
echo ""
echo "Note: This setup will incur charges for the NAT Gateway (~$45/month) and Elastic IP."