#!/usr/bin/env python3

import boto3
import json
from botocore.exceptions import ClientError

def create_dynamodb_table():
    """Create DynamoDB table for Ansible inventory with optimal configuration"""
    
    dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
    
    table_name = 'ansible-inventory'
    
    try:
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=table_name)
            print(f"✓ Table '{table_name}' already exists")
            print(f"Status: {response['Table']['TableStatus']}")
            return response['Table']['TableArn']
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create table
        print(f"Creating DynamoDB table: {table_name}")
        
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'instance_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'record_type',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'instance_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'record_type',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            Tags=[
                {
                    'Key': 'Purpose',
                    'Value': 'Ansible-Inventory'
                },
                {
                    'Key': 'Environment',
                    'Value': 'Production'
                }
            ]
        )
        
        print(f"✓ Table creation initiated")
        print(f"Table ARN: {response['TableDescription']['TableArn']}")
        
        # Wait for table to be active
        print("Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"✓ Table '{table_name}' is now active and ready to use")
        return response['TableDescription']['TableArn']
        
    except ClientError as e:
        print(f"Error creating table: {e}")
        return None

def main():
    print("=== DynamoDB Ansible Inventory Setup ===")
    
    # Create table
    table_arn = create_dynamodb_table()
    if not table_arn:
        print("Failed to create table. Exiting.")
        return
    
    print(f"\n=== Setup Complete ===")
    print(f"Table Name: ansible-inventory")
    print(f"Region: ap-south-1")
    print(f"Billing: Pay-per-request")
    print(f"\nReady for use!")

if __name__ == "__main__":
    main()
