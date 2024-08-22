
# VARIABLES # for you to edit!

locals {
  name      = "flux"
  pwd       = basename(path.cwd)
  region    = "us-east-2"
  ami       = "ami-08d05be2ce544c8e3"
  placement = "performance-study"

  instance_type = "hpc6a.48xlarge"
  vpc_cidr      = "10.0.0.0/16"
  key_name      = "dinosaur-performance-study"

  # both hpc7g and hpc6a have ens5
  ethernet_device = "ens5"

  # Must be larger than ami. I made this big to support a lot of containers...
  volume_size = 200

  # Set autoscaling to consistent size so we don't scale for now
  # We need one extra for the control plane, etc for a size 32 cluster
  min_size     = 2
  max_size     = 2
  desired_size = 2

  cidr_block_a = "10.0.1.0/24"
  cidr_block_b = "10.0.2.0/24"
  cidr_block_c = "10.0.3.0/24"

  # "0.0.0.0/0" allows from anywhere - update
  # this to be just your ip / collaborators
  ip_address_allowed = ["0.0.0.0/0"]

}

# Add our ip address to the ssh config block
data "http" "address" {
  url = "https://ipv4.icanhazip.com"
}


# Example queries to get public ip addresses or private DNS names
# aws ec2 describe-instances --region us-east-1 --filters "Name=tag:selector,Values=flux-selector" | jq .Reservations[].Instances[].NetworkInterfaces[].PrivateIpAddress
# aws ec2 describe-instances --region us-east-1 --filters "Name=tag:selector,Values=flux-selector" | jq .Reservations[].Instances[].NetworkInterfaces[].PrivateIpAddresses[].PrivateDnsName

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.49.0"
    }
  }
}

# Read in a shared script to init / finalize the flux setup
data "template_file" "startup_script" {
  template = templatefile("start-script.sh", {
    selector_name   = local.name,
    desired_size    = local.desired_size
    ethernet_device = local.ethernet_device
    region          = local.region
  })
}

provider "aws" {
  region = local.region
}

# https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html
resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "${local.name}-vpc"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.cidr_block_b
  availability_zone = "${local.region}b"

  enable_resource_name_dns_a_record_on_launch = true
  private_dns_hostname_type_on_launch         = "resource-name"

  tags = {
    Name = "${local.name}-subnet-public-b"
  }
}

resource "aws_subnet" "public_c" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.cidr_block_c
  availability_zone = "${local.region}c"

  enable_resource_name_dns_a_record_on_launch = true
  private_dns_hostname_type_on_launch         = "resource-name"

  tags = {
    Name = "${local.name}-subnet-public-c"
  }
}

resource "aws_internet_gateway" "main_gateway" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name}-main-gateway"
  }
}

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main_gateway.id
  }

  tags = {
    Name = "${local.name}-public-route-table"
  }
}

resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "c" {
  subnet_id      = aws_subnet.public_c.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_security_group" "security_group" {
  name   = "${local.name}-security-group"
  vpc_id = aws_vpc.main.id

  ingress {
    description = "Allow http from everywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # This is essential for efa!
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = -1
    self      = true
  }
  egress {
    from_port = 0
    to_port   = 0
    protocol  = -1
    self      = true
  }

  # temporariliy allowing all protocols for internal communication
  ingress {
    description = "Allow internal traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [local.cidr_block_a, local.cidr_block_b, local.cidr_block_c]
  }

  # This could be scoped better to internal instances
  ingress {
    description = "Allow http on port 8050 for flux"
    from_port   = 8050
    to_port     = 8050
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow ssh from deployer computer"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.address.response_body)}/32"]
  }

  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    protocol    = "icmp"
    from_port   = 8
    to_port     = 0
    description = "Allow pings"
  }

  egress {
    description = "Allow outgoing traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-security-group"
  }
}

resource "aws_lb" "load_balancer" {
  name               = "${local.name}-load-balancer"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.security_group.id]
  subnets            = [aws_subnet.public_b.id, aws_subnet.public_c.id]
}

resource "aws_lb_listener" "load_balance_listener" {
  load_balancer_arn = aws_lb.load_balancer.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.target_group.arn
  }
}

resource "aws_lb_target_group" "target_group" {
  name        = "${local.name}-target-group"
  target_type = "instance"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
}


# Create an IAM instance profile to allow using the awscli

resource "aws_iam_policy" "ec2_policy" {
  name        = "${local.name}-ec2-policy"
  path        = "/"
  description = "Policy to allow listing instances"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [{
      "Effect" : "Allow",
      "Action" : [
        "ec2:DescribeInstances",
        "ec2:DescribeImages",
        "ec2:DescribeTags",
        "ec2:DescribeSnapshots",
        "ec2:DescribeInstanceTopology",
      ],
      "Resource" : "*"
    }]
  })
}

# The trust policy specifies who or what can assume the role
# The permission policy specify the actions available on what resources
resource "aws_iam_role" "ec2_role" {
  name = "${local.name}-ec2-role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [{
      "Effect" = "Allow",
      "Action" = "sts:AssumeRole",
      "Sid"    = ""
      "Principal" = {
        "Service" = "ec2.amazonaws.com"
      }
    }],
  })
}


# Attach the role to the policy file
resource "aws_iam_policy_attachment" "ec2_policy_role" {
  name       = "${local.name}-ec2-attachment"
  roles      = [aws_iam_role.ec2_role.name]
  policy_arn = aws_iam_policy.ec2_policy.arn
}

# Create an instance profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${local.name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

resource "aws_launch_template" "launch_template" {
  name          = "${local.name}-launch_template"
  image_id      = local.ami
  instance_type = local.instance_type
  key_name      = local.key_name
  user_data     = base64encode(data.template_file.startup_script.rendered)

  # So we can use the AWS client
  iam_instance_profile {
    # arn = aws_iam_instance_profile.iam_profile.arn
    name = aws_iam_instance_profile.ec2_profile.name
  }
  block_device_mappings {
    device_name = "/dev/sda1"

    ebs {
      volume_size = local.volume_size
      volume_type = "gp2"
    }
  }

  # https://github.com/terraform-aws-modules/terraform-aws-autoscaling/blob/master/examples/complete/main.tf
  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.security_group.id]
    description                 = "Elastic Fiber Adapted (EFA)"
    delete_on_termination       = true
    device_index                = 0
    interface_type              = "efa"
  }
}


resource "aws_autoscaling_group" "autoscaling_group" {
  name              = "${local.name}-autoscaling-group"
  max_size          = local.min_size
  min_size          = local.max_size
  health_check_type = "EC2"
  placement_group   = local.placement

  # This is 25 hours, lord help me if I'm still running experiments that long...
  health_check_grace_period = 90000
  capacity_rebalance        = false

  # Make this really large so we don't check soon :)
  desired_capacity  = local.desired_size
  target_group_arns = [aws_lb_target_group.target_group.arn]

  # IMPORTANT: usernetes won't be able to talk to the internet addresses in different subnets
  # but we are required to create them otherwise cloudformation gets angry 
  # We do not want to make cloud formation angry :)
  vpc_zone_identifier = [aws_subnet.public_b.id]
  # default_cooldown is unset

  # These could also be selected based on the asg, e.g.,
  # "aws:autoscaling:groupName"
  # "flux-autoscaling-group"
  tag {
    key                 = "selector"
    value               = "${local.name}-selector"
    propagate_at_launch = true
  }

  launch_template {
    id      = aws_launch_template.launch_template.id
    version = "$Latest"
  }
}
