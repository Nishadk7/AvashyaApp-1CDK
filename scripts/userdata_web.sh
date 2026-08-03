#!/bin/bash
yum update -y
yum install -y python3 git nginx amazon-cloudwatch-agent

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
            "file_path": "/home/ec2-user/AvashyaApp-1/web_tier.log",
            "log_group_name": "/aws/ec2/NishadInternsip-AvashyaApp/WebTier",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S"
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/aws/ec2/NishadInternsip-AvashyaApp/NginxAccess",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Clone Repository
cd /home/ec2-user
if [ ! -d "AvashyaApp-1" ]; then
    git clone https://github.com/Nishadk7/AvashyaApp-1.git
fi
cd AvashyaApp-1
git pull origin main
chown -R ec2-user:ec2-user /home/ec2-user/AvashyaApp-1

# Configure frontend API endpoint
echo 'window.API_BASE = "/api";' > /home/ec2-user/AvashyaApp-1/frontend/config.js

# Configure Nginx Reverse Proxy pointing to Internal ALB DNS
cat << 'EOF' > /etc/nginx/conf.d/avashya_web.conf
server {
    listen 80;
    server_name _;

    location / {
        root /home/ec2-user/AvashyaApp-1/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://${INTERNAL_ALB_DNS}:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

chmod 755 /home/ec2-user /home/ec2-user/AvashyaApp-1 /home/ec2-user/AvashyaApp-1/frontend
systemctl enable nginx
systemctl restart nginx

su - ec2-user -c "cd /home/ec2-user/AvashyaApp-1 && nohup python3 -u frontend/server.py > web_tier.log 2>&1 &"
