#!/usr/bin/env python3

import json
import yaml
import os
import glob
import boto3
import subprocess
from datetime import datetime
from botocore.exceptions import ClientError

# DynamoDB Configuration
DYNAMODB_TABLE = 'ansible-inventory'
DYNAMODB_REGION = 'ap-south-1'

def get_dynamodb_table():
    """Get DynamoDB table resource"""
    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    return dynamodb.Table(DYNAMODB_TABLE)

def store_server_in_db(server_config):
    """Store server details in DynamoDB"""
    table = get_dynamodb_table()
    
    try:
        table.put_item(
            Item={
                'instance_id': server_config['server']['instance_id'],
                'record_type': 'SERVER',
                'server_name': server_config['server']['name'],
                'region': server_config['server']['region'],
                'os_type': server_config['os']
            }
        )
        print(f"✓ Stored server {server_config['server']['name']} in DynamoDB")
    except ClientError as e:
        print(f"Error storing server in DynamoDB: {e}")

def get_server_from_db(server_name):
    """Fetch server details from DynamoDB by server name"""
    table = get_dynamodb_table()
    
    try:
        # Scan table to find server by name (since server_name is not a key)
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('server_name').eq(server_name) & 
                           boto3.dynamodb.conditions.Attr('record_type').eq('SERVER')
        )
        
        if response['Items']:
            return response['Items'][0]  # Return first match
        else:
            return None
            
    except ClientError as e:
        print(f"Error fetching server from DynamoDB: {e}")
        return None

def list_existing_servers():
    """List all existing servers from DynamoDB"""
    table = get_dynamodb_table()
    
    try:
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('record_type').eq('SERVER')
        )
        
        servers = []
        for item in response['Items']:
            servers.append(item['server_name'])
        
        return sorted(servers)
        
    except ClientError as e:
        print(f"Error listing servers: {e}")
        return []
    """Update software installation status in DynamoDB"""
    table = get_dynamodb_table()
    
    try:
        table.put_item(
            Item={
                'instance_id': instance_id,
                'record_type': f'SOFTWARE#{software_name}',
                'software_name': software_name,
                'installed_date': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'installation_status': status
            }
        )
        print(f"✓ Updated {software_name} status: {status}")
    except ClientError as e:
        print(f"Error updating software status: {e}")

def run_ansible_playbook(inventory_file, playbook_file):
    """Execute ansible playbook and return result"""
    print(f"\n=== Running Ansible Playbook ===")
    print(f"Command: ansible-playbook -i {inventory_file} {playbook_file}")
    
    try:
        result = subprocess.run(
            ['ansible-playbook', '-i', inventory_file, playbook_file],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        print(f"\nPlaybook Output:")
        print(result.stdout)
        
        if result.stderr:
            print(f"\nErrors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Playbook execution timed out (30 minutes)")
        return False
    except FileNotFoundError:
        print("Error: ansible-playbook command not found. Please install Ansible.")
        return False
    except Exception as e:
        print(f"Error running playbook: {e}")
        return False

def get_server_details():
    """Collect server details - new or existing"""
    print("=== Server Configuration ===")
    
    # Get number of target servers
    while True:
        try:
            num_servers = int(input("Enter number of target servers: ").strip())
            if num_servers > 0:
                break
            print("Please enter a positive number")
        except ValueError:
            print("Please enter a valid number")
    
    servers = []
    
    for i in range(num_servers):
        print(f"\n--- Server {i+1} ---")
        
        # Ask if new or existing server
        while True:
            server_type = input("Is this a new server or existing? (new/existing): ").strip().lower()
            if server_type in ['new', 'existing']:
                break
            print("Please enter 'new' or 'existing'")
        
        if server_type == 'new':
            # Get new server details
            server_name = input("Enter server name: ").strip()
            instance_id = input("Enter Instance ID: ").strip()
            region = input("Enter AWS Region: ").strip()
            
            print("Available OS: ubuntu, centos, debian, amazonlinux")
            os_type = input("Enter OS type: ").strip().lower()
            if os_type not in ['ubuntu', 'centos', 'debian', 'amazonlinux']:
                print(f"Warning: Invalid OS '{os_type}', defaulting to 'ubuntu'")
                os_type = 'ubuntu'
            
            s3_bucket = input("Enter S3 Bucket Name (for SSM): ").strip()
            
            servers.append({
                'name': server_name,
                'instance_id': instance_id,
                'region': region,
                'os_type': os_type,
                'bucket_name': s3_bucket,
                'is_new': True
            })
            
        else:  # existing server
            # List existing servers
            existing_servers = list_existing_servers()
            if not existing_servers:
                print("No existing servers found in database. Please add as new server.")
                continue
            
            print("\nExisting servers:")
            for idx, server in enumerate(existing_servers, 1):
                print(f"  {idx}. {server}")
            
            server_name = input("Enter server name from the list above: ").strip()
            
            # Fetch server details from DB
            server_data = get_server_from_db(server_name)
            if not server_data:
                print(f"Server '{server_name}' not found in database.")
                continue
            
            servers.append({
                'name': server_data['server_name'],
                'instance_id': server_data['instance_id'],
                'region': server_data['region'],
                'os_type': server_data['os_type'],
                'bucket_name': '',  # Will be asked later if needed
                'is_new': False
            })
    
    return servers

def get_available_roles():
    """Dynamically get available roles from roles directory"""
    roles_dir = "roles"
    if not os.path.exists(roles_dir):
        return []
    
    available_roles = []
    for role_dir in os.listdir(roles_dir):
        role_path = os.path.join(roles_dir, role_dir)
        if os.path.isdir(role_path) and os.path.exists(os.path.join(role_path, "tasks")):
            available_roles.append(role_dir)
    
    return sorted(available_roles)

def get_available_os_for_role(role_name):
    """Get available OS files for a specific role"""
    tasks_dir = f"roles/{role_name}/tasks"
    if not os.path.exists(tasks_dir):
        return []
    
    os_files = glob.glob(f"{tasks_dir}/*.yml")
    available_os = [os.path.basename(f).replace('.yml', '') for f in os_files]
    return sorted(available_os)

def get_software_requirements(servers):
    """Collect software installation requirements for each server"""
    print("\n=== Software Selection ===")
    available_software = get_available_roles()
    
    if not available_software:
        print("No roles found in roles directory")
        return []
    
    print("Available software:", ', '.join(available_software))
    
    server_configs = []
    for server in servers:
        print(f"\n--- Software for {server['name']} ({server['instance_id']}) ---")
        
        # Get software for this server
        selected_software = input(f"Enter software to install on {server['name']} (comma-separated): ").strip().split(',')
        selected_software = [s.strip().lower() for s in selected_software if s.strip()]
        
        # Validate selections
        invalid_software = [s for s in selected_software if s not in available_software]
        if invalid_software:
            print(f"Warning: Invalid software: {invalid_software}")
            selected_software = [s for s in selected_software if s in available_software]
        
        # Ask for S3 bucket if not provided (for existing servers)
        if not server['bucket_name'] and selected_software:
            server['bucket_name'] = input(f"Enter S3 Bucket Name for {server['name']}: ").strip()
        
        server_configs.append({
            'server': server,
            'os': server['os_type'],
            'software': selected_software
        })
    
    return server_configs

def create_inventory_file(server_configs):
    """Generate inventory.yml file for multiple servers"""
    inventory = {'all': {'hosts': {}}}
    
    for config in server_configs:
        server = config['server']
        inventory['all']['hosts'][server['name']] = {
            'ansible_host': server['instance_id'],
            'ansible_connection': 'aws_ssm',
            'ansible_aws_ssm_region': server['region'],
            'ansible_aws_ssm_bucket_name': server['bucket_name']
        }
    
    with open('inventory.yml', 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False, indent=2)
    
    print("✓ Created inventory.yml")

def create_main_playbook(server_configs):
    """Generate main.yml playbook file for multiple servers"""
    playbooks = []
    
    for config in server_configs:
        server = config['server']
        target_os = config['os']
        software_list = config['software']
        
        if software_list:
            playbook = {
                'name': f'Install software on {server["name"]}',
                'hosts': server['name'],
                'become': True,
                'tasks': []
            }
            
            # Add tasks for each selected software
            for software in software_list:
                task = {
                    'name': f'Install {software}',
                    'include_role': {
                        'name': software,
                        'tasks_from': f'{target_os}.yml'
                    }
                }
                playbook['tasks'].append(task)
            
            playbooks.append(playbook)
    
    with open('main.yml', 'w') as f:
        yaml.dump(playbooks, f, default_flow_style=False, indent=2)
    
    print("✓ Created main.yml")

def main():
    print("Ansible Setup Script with DynamoDB Integration")
    print("=" * 50)
    
    # Collect server details (new or existing)
    servers = get_server_details()
    server_configs = get_software_requirements(servers)
    
    if not any(config['software'] for config in server_configs):
        print("No valid software selected for any server. Exiting.")
        return
    
    # Store new servers in DynamoDB
    print(f"\n=== Storing New Server Details in DynamoDB ===")
    for config in server_configs:
        if config['server']['is_new']:
            store_server_in_db(config)
        else:
            print(f"✓ Using existing server {config['server']['name']} from DynamoDB")
    
    # Generate files
    print(f"\n=== Generating Ansible Files ===")
    create_inventory_file(server_configs)
    create_main_playbook(server_configs)
    
    # Execute playbook and update status
    print(f"\n=== Executing Playbook ===")
    success = run_ansible_playbook('inventory.yml', 'main.yml')
    
    # Update installation status in DynamoDB
    print(f"\n=== Updating Installation Status ===")
    status = "success" if success else "failed"
    
    for config in server_configs:
        instance_id = config['server']['instance_id']
        for software in config['software']:
            update_software_status(instance_id, software, status)
    
    # Summary
    print(f"\n=== Summary ===")
    for config in server_configs:
        server = config['server']
        server_type = "New" if server['is_new'] else "Existing"
        software_list = ', '.join(config['software']) if config['software'] else 'None'
        print(f"{server['name']} ({server_type}): {server['instance_id']} - Software: {software_list} - Status: {status}")
    
    print(f"\nPlaybook execution: {'SUCCESS' if success else 'FAILED'}")
    print(f"All details stored in DynamoDB table: {DYNAMODB_TABLE}")_main_playbook(server_configs)
    
    # Execute playbook and update status
    print(f"\n=== Executing Playbook ===")
    success = run_ansible_playbook('inventory.yml', 'main.yml')
    
    # Update installation status in DynamoDB
    print(f"\n=== Updating Installation Status ===")
    status = "success" if success else "failed"
    
    for config in server_configs:
        instance_id = config['server']['instance_id']
        for software in config['software']:
            update_software_status(instance_id, software, status)
    
    # Summary
    print(f"\n=== Summary ===")
    for config in server_configs:
        server = config['server']
        software_list = ', '.join(config['software']) if config['software'] else 'None'
        print(f"{server['name']}: {server['instance_id']} - Software: {software_list} - Status: {status}")
    
    print(f"\nPlaybook execution: {'SUCCESS' if success else 'FAILED'}")
    print(f"All details stored in DynamoDB table: {DYNAMODB_TABLE}")

if __name__ == "__main__":
    main()
