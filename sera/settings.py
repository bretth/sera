from string import Template
# AWS long poll


LIFT_CMD = ''
LOWER_CMD = ''
DEFAULT_TIMEOUT = 60

# time to re-lift in minutes
RESET_TIME = 60

service_template = Template("""
[Unit]
Description=Sera remote
After=network.target

[Service]
ExecStart=${executable} watch
Type=simple
User=${user}
Restart=always

[Install]
WantedBy=multi-user.target
""")
