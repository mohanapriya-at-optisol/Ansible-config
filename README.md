# Ansible Automation with DynamoDB Integration

A comprehensive Ansible automation solution that manages server inventory in DynamoDB and executes software installations via AWS Systems Manager (SSM).

## 🚀 Features

- **Persistent Inventory**: Server details stored in DynamoDB for reuse
- **SSM Integration**: Secure connections to EC2 instances without SSH keys
- **Multi-OS Support**: Ubuntu, CentOS, Debian, Amazon Linux 2023
- **Installation Tracking**: Records success/failure status for all software installations
- **Automated Playbook Execution**: Generates and runs Ansible playbooks automatically
- **Environment Configuration**: Configurable via .env files

## 📋 Prerequisites

### AWS Requirements
- EC2 instances with SSM Agent installed and running
- IAM role with permissiona for:
  - DynamoDB (read/write access)
  - SSM (session management)
  - S3 (for SSM session logging if enabled)

## 🛠️ Installation

### 1. Clone and Setup
```bash
git clone <repository-url>
cd ansible-automation
```

### 2. Install Dependencies
```bash
pip install -r requirements_dynamodb.txt
```

### 3. Configure Environment
Edit `.env` file:
```bash
DYNAMODB_TABLE=ansible-inventory
DYNAMODB_REGION=ap-south-1
```

### 4. Create DynamoDB Table
```bash
python3 setup_dynamodb.py
```

### 5. Setup Ansible Roles
Ensure your roles directory structure:
```
roles/
├── docker/
│   └── tasks/
│       ├── ubuntu.yml
│       ├── centos.yml
│       └── amazonlinux.yml
├── nginx/
│   └── tasks/
│       └── ubuntu.yml
└── grafana/
    └── tasks/
        └── ubuntu.yml
```

## 🎯 Usage

### Run the Main Script
```bash
python3 setup_ansible_fixed.py
```

### Interactive Workflow

#### 1. Server Configuration
```
Enter number of target servers: 2

--- Server 1 ---
Is this a new server or existing? (new/existing): new
Enter server name: web-server-1
Enter Instance ID: i-0123456789abcdef0
Enter AWS Region: ap-south-1
Available OS: ubuntu, centos, debian, amazonlinux, amazonlinux2023
Enter OS type: ubuntu
Enter S3 Bucket Name (for SSM): my-ssm-logs-bucket

--- Server 2 ---
Is this a new server or existing? (new/existing): existing
Existing servers:
  1. web-server-1
  2. db-server-1
Enter server name: db-server-1
```

#### 2. Software Selection
```
Available software: docker, nginx, grafana, jenkins

--- Software for web-server-1 (i-0123456789abcdef0) ---
Enter software to install: docker, nginx

--- Software for db-server-1 (i-0987654321fedcba0) ---
Enter software to install: grafana
```

#### 3. Automated Execution
The script will:
- Store new servers in DynamoDB
- Generate `inventory.yml` and `main.yml`
- Execute the Ansible playbook
- Update installation status in DynamoDB

## 📊 DynamoDB Schema

### Server Records
```json
{
  "instance_id": "i-0123456789abcdef0",
  "record_type": "SERVER",
  "server_name": "web-server-1",
  "region": "ap-south-1",
  "os_type": "ubuntu",
  "s3_bucket_name": "my-ssm-logs-bucket"
}
```

### Software Records
```json
{
  "instance_id": "i-0123456789abcdef0",
  "record_type": "SOFTWARE#docker",
  "software_name": "docker",
  "installed_date": "2024-01-30T14:30:22Z",
  "installation_status": "success"
}
```

## 🔧 Configuration Files

### .env File
```bash
# DynamoDB Configuration
DYNAMODB_TABLE=ansible-inventory
DYNAMODB_REGION=ap-south-1



## 📁 Project Structure

```
ansible-automation/
├── .env                          # Environment configuration
├── setup_dynamodb.py            # DynamoDB table creation
├── setup_ansible_fixed.py       # Main automation script
├── requirements_dynamodb.txt    # Python dependencies
├── roles/                       # Ansible roles
│   ├── docker/
│   ├── nginx/
│   ├── grafana/
│   └── jenkins/
├── inventory.yml               # Generated inventory (auto-created)
├── main.yml                   # Generated playbook (auto-created)
└── README.md                 # This file
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Missing OS Files
```
Error: Could not find specified file in role: tasks/amazonlinux.yml
```
**Solution**: Create missing OS-specific task files or use symlinks:
```bash
cd roles/nodeexporter/tasks
ln -s amazonlinux2023.yml amazonlinux.yml
```

#### 2. SSM Connection Issues
```
Error: Failed to connect via SSM
```
**Solution**: Verify:
- SSM Agent is running on EC2 instance
- IAM role has SSM permissions
- S3 bucket exists and is accessible

#### 3. DynamoDB Access Issues
```
Error: Unable to access DynamoDB table
```
**Solution**: Check:
- AWS credentials are configured
- IAM permissions for DynamoDB
- Table exists in correct region

### Debug Mode
Add debug output to playbook execution:
```bash
# Edit the script to add -vvv flag
['ansible-playbook', '-vvv', '-i', inventory_file, playbook_file]
```

