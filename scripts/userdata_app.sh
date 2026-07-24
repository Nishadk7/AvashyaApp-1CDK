#!/bin/bash
yum update -y
yum install -y python3 python3-pip git postgresql15 amazon-cloudwatch-agent

# CloudWatch Agent Configuration
mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/
cat << 'EOF' > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/home/ec2-user/AvashyaApp-1/app_tier.log",
            "log_group_name": "/aws/ec2/AvashyaApp/AppTier",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S"
          }
        ]
      }
    }
  }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Export Environment Variables
echo "export RDS_ENDPOINT='${RDS_ENDPOINT}'" > /etc/profile.d/avashya_env.sh
echo "export RDSHOST='${RDS_ENDPOINT}'" >> /etc/profile.d/avashya_env.sh
echo "export RDS_HOSTNAME='${RDS_ENDPOINT}'" >> /etc/profile.d/avashya_env.sh
echo "export DB_HOST='${RDS_ENDPOINT}'" >> /etc/profile.d/avashya_env.sh
echo "export POSTGRES_HOST='${RDS_ENDPOINT}'" >> /etc/profile.d/avashya_env.sh
echo "export DATABASE_HOST='${RDS_ENDPOINT}'" >> /etc/profile.d/avashya_env.sh
echo "export DBUSER='postgres'" >> /etc/profile.d/avashya_env.sh
echo "export DBNAME='avashyadadb'" >> /etc/profile.d/avashya_env.sh
echo "export DBPASSWORD='${DBPASSWORD}'" >> /etc/profile.d/avashya_env.sh
echo "export S3_BUCKET_NAME='${S3_BUCKET_NAME}'" >> /etc/profile.d/avashya_env.sh
echo "export AWS_DEFAULT_REGION='${AWS_REGION}'" >> /etc/profile.d/avashya_env.sh
chmod +x /etc/profile.d/avashya_env.sh
source /etc/profile.d/avashya_env.sh

# Clone Repository
cd /home/ec2-user
if [ ! -d "AvashyaApp-1" ]; then
    git clone https://github.com/Nishadk7/AvashyaApp-1.git
fi
cd AvashyaApp-1
git pull origin main

chown -R ec2-user:ec2-user /home/ec2-user/AvashyaApp-1

# Virtual environment setup and execution (Explicitly source avashya_env.sh)
su - ec2-user -c "cd /home/ec2-user/AvashyaApp-1 && python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt"
su - ec2-user -c "source /etc/profile.d/avashya_env.sh && cd /home/ec2-user/AvashyaApp-1 && ./aws/start_app_ec2.sh"
