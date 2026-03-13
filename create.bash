#!/bin/bash

set -euo pipefail

#
# Pre-reqs:
#   1. requires zip command-line utility
#   2. requires python3
#   3. requires setup of AWSCLI
#   4. requires aws EB CLI
#         pip3 install awsebcli --upgrade --user
#

#
# Application variables:
#
APP_NAME="vod-highlights-backend"
ENV_NAME="vod-highlights-backend-env"
REGION="us-east-2"
PLATFORM="Node.js"
HARDWARE="t3.micro"
ZIPFILE="backend.zip"
APP_DIR="backend"
INSTANCE_PROFILE="${EB_INSTANCE_PROFILE:-aws-elasticbeanstalk-ec2-role}"
SERVICE_ROLE="${EB_SERVICE_ROLE:-}"

#
# Network-related variables:
#
# Set these if you want to launch into a specific VPC/subnets.
# Leave as-is to let Elastic Beanstalk pick defaults.
VPCID=""
VPCSUBGROUPS=""

AWS_REGION="${AWS_REGION:-$REGION}"

#
# start of script:
#
echo ""
echo "1. initializing EB"

eb init $APP_NAME \
        --platform $PLATFORM \
        --region $REGION

#
# drop down into backend/ sub-dir and zip the contents:
#
echo ""
echo "2. packaging app"
rm -f *.zip &> /dev/null
pushd ./$APP_DIR &> /dev/null
rm -f *.zip &> /dev/null
zip -r $ZIPFILE . \
  -x "node_modules/*" \
     "*.log" \
     "npm-debug.log*" \
     ".DS_Store" \
     ".git/*" \
     ".env" \
     ".env.*"
mv $ZIPFILE .. &> /dev/null
popd &> /dev/null

#
# now create a new web service and deploy the .zip:
# NOTE: we create with AWS sample app, then update with
# our app. This is the simplest way to bootstrap the env.
#
echo ""
echo "3. Creating environment on EB..."

CREATE_ARGS=(
  "$ENV_NAME"
  "--instance_type" "$HARDWARE"
  "--platform" "$PLATFORM"
  "--instance_profile" "$INSTANCE_PROFILE"
  "--single"
  "--sample"
)

if [[ -n "$SERVICE_ROLE" ]]; then
  CREATE_ARGS+=("--service-role" "$SERVICE_ROLE")
fi

if [[ -n "$VPCID" && -n "$VPCSUBGROUPS" ]]; then
  CREATE_ARGS+=("--vpc.id" "$VPCID" "--vpc.ec2subnets" "$VPCSUBGROUPS")
  eb create "${CREATE_ARGS[@]}"
else
  eb create "${CREATE_ARGS[@]}"
fi

echo ""
echo "4. Deploying app to EB..."

eb deploy $ENV_NAME \
         --archive $ZIPFILE \
         --region $REGION

echo ""
echo "Done! You can use 'eb status' to check status of web service."
echo ""
