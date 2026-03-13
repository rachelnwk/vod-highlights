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
ZIPFILE="backend.zip"
APP_DIR="backend"
UNIQUE_ID=$(date +%Y%m%d-%H%M%S)
VERSION=$UNIQUE_ID-$ZIPFILE

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
mv $ZIPFILE ../$VERSION &> /dev/null
popd &> /dev/null

#
# now deploy the .zip:
# NOTE: the .zip file name is changed to be unique
# based on date/time so EB detects a new app version.
#
echo ""
echo "3. Deploying app to EB..."

eb deploy $ENV_NAME \
         --archive $VERSION \
         --region $REGION

echo ""
echo "Done! You can use 'eb status' to check status of web service."
echo ""
