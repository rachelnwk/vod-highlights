#!/bin/bash

set -euo pipefail

#
# Pre-reqs:
#   1. requires python3
#   2. requires setup of AWSCLI (see project 01, part 01)
#   3. requires aws EB CLI
#         pip3 install awsebcli --upgrade --user
#

#
# Application variables:
#
APP_NAME="vod-highlights-backend"
ENV_NAME="vod-highlights-backend-env"
REGION="us-east-2"
PLATFORM="Node.js"

#
# helper functions:
#
get_environment_status() {
  aws elasticbeanstalk describe-environments \
          --environment-names "$ENV_NAME" \
          --region "$REGION" \
          --query "Environments[0].Status" \
          --output text \
          --no-cli-pager 2>/dev/null || echo "None"
}

#
# start of script:
#
echo ""
echo "1. initializing EB"

eb init $APP_NAME \
        --platform $PLATFORM \
        --region $REGION 

#
# delete the application, which then deletes everything else:
#
echo ""
echo "2. deleting app"

rm -f *.zip &> /dev/null

ENV_STATUS=$(get_environment_status)
if [[ "$ENV_STATUS" == "None" || "$ENV_STATUS" == "Terminated" ]]; then
  echo "Environment $ENV_NAME does not exist. Nothing to delete."
  exit 0
fi

eb terminate --all --force $APP_NAME
