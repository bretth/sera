from string import Template
# AWS long poll


LIFT_CMD = ''
LOWER_CMD = ''
TIMEOUT = 20

# time to re-lift
RESET_TIME = 300

service_template = Template("""
[Unit]
Description=Sera remote
After=network.target

[Service]
ExecStart="${executable} watch"
Type=simple

[Install]
WantedBy=multi-user.target
""")
