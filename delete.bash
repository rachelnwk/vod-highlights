#!/bin/bash

#
# Pre-reqs:
#   1. requires python3
#   2. requires setup of AWSCLI
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

eb terminate --all --force $APP_NAME
