#!/bin/bash

set -euo pipefail

#
# Pre-reqs:
#   1. requires zip command-line utility
#   2. requires python3
#   3. requires setup of AWSCLI (see project 01, part 01)
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
WORKER_DIR="worker"
STAGING_DIR="eb-staging"
DEPLOYMENT_COMMAND_TIMEOUT="1800"
ROOT_VOLUME_SIZE="30"
UNIQUE_ID=$(date +%Y%m%d-%H%M%S)
VERSION=$UNIQUE_ID-$ZIPFILE

#
# Network-related variables:
#
VPCID="vpc-0333867079a8445f5"
VPCSUBGROUPS="subnet-09adb3f8cec6e3206,subnet-0ece757313b262198,subnet-02134cd9e95b57907"

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

get_environment_id() {
  aws elasticbeanstalk describe-environments \
          --environment-names "$ENV_NAME" \
          --region "$REGION" \
          --query "Environments[0].EnvironmentId" \
          --output text \
          --no-cli-pager 2>/dev/null || echo "None"
}

stack_exists_for_environment() {
  local env_id="$1"
  local stack_name="awseb-${env_id}-stack"

  aws cloudformation describe-stacks \
          --stack-name "$stack_name" \
          --region "$REGION" \
          --no-cli-pager >/dev/null 2>&1
}

wait_for_environment_ready() {
  local step_label="$1"
  local status=""
  local attempt=0
  local max_attempts=40

  echo ""
  echo "$step_label"

  while true; do
    status=$(get_environment_status)

    if [[ "$status" == "Ready" ]]; then
      break
    fi

    if [[ "$status" == "None" || "$status" == "Terminated" || "$status" == "Terminating" ]]; then
      echo "Environment entered status '$status'. Check EB events/logs before retrying."
      exit 1
    fi

    attempt=$((attempt + 1))
    if [[ $attempt -ge $max_attempts ]]; then
      echo "Environment did not reach Ready state in time. Check 'eb status' or the AWS console."
      exit 1
    fi

    echo "   current status: $status"
    sleep 15
  done
}

#
# start of script:
#
echo ""
echo "1. initializing EB"

eb init $APP_NAME \
        --platform $PLATFORM \
        --region $REGION 

EXISTING_STATUS=$(get_environment_status)
if [[ "$EXISTING_STATUS" != "None" && "$EXISTING_STATUS" != "Terminated" ]]; then
  EXISTING_ID=$(get_environment_id)

  if [[ "$EXISTING_ID" != "None" ]] && ! stack_exists_for_environment "$EXISTING_ID"; then
    echo "Environment $ENV_NAME already exists in Elastic Beanstalk, but stack awseb-${EXISTING_ID}-stack is missing."
    echo "Delete the stale environment record or choose a new environment name before rerunning ./create.bash."
    echo "Suggested cleanup command:"
    echo "  aws elasticbeanstalk terminate-environment --environment-name $ENV_NAME --force-terminate --region $REGION --no-cli-pager"
    exit 1
  fi

  echo "Environment $ENV_NAME already exists with status '$EXISTING_STATUS'."
  echo "Use ./update.bash for code changes or delete the environment before rerunning ./create.bash."
  exit 1
fi

#
# package the backend, worker, Procfile, and EB hooks
# into one deployable bundle:
#
echo ""
echo "2. packaging app"
rm -f *.zip &> /dev/null
rm -rf ./$STAGING_DIR &> /dev/null
mkdir ./$STAGING_DIR
cp -R ./$APP_DIR/. ./$STAGING_DIR/
cp -R ./$WORKER_DIR ./$STAGING_DIR/$WORKER_DIR
cp ./Procfile ./$STAGING_DIR/Procfile

if [[ -d "./.platform" ]]; then
  mkdir -p ./$STAGING_DIR/.platform
  cp -R ./.platform/. ./$STAGING_DIR/.platform/
fi

rm -rf ./$STAGING_DIR/node_modules &> /dev/null
rm -rf ./$STAGING_DIR/$WORKER_DIR/.venv &> /dev/null
rm -rf ./$STAGING_DIR/$WORKER_DIR/temp &> /dev/null
find ./$STAGING_DIR -name "*.log" -delete
find ./$STAGING_DIR -name "npm-debug.log*" -delete
find ./$STAGING_DIR -name ".DS_Store" -delete
find ./$STAGING_DIR -name "__pycache__" -type d -prune -exec rm -rf {} +
find ./$STAGING_DIR -name "*.pyc" -delete
find ./$STAGING_DIR -name "*.pyo" -delete

pushd ./$STAGING_DIR &> /dev/null
zip -r "$ZIPFILE" .
mv "$ZIPFILE" "../$VERSION" &> /dev/null
popd &> /dev/null
rm -rf ./$STAGING_DIR &> /dev/null

#
# now create a new web service and deploy the .zip:
# NOTE: we create with AWS sample app, then update with
# our app. Strange, but it's the simplest way to work 
# with .zip files of our code.
#
echo ""
echo "3. Creating environment on EB..."

eb create $ENV_NAME \
          --instance_type $HARDWARE \
          --platform $PLATFORM \
          --vpc.id $VPCID \
          --vpc.ec2subnets $VPCSUBGROUPS \
          --single \
          --sample \
          --service-role aws-elasticbeanstalk-service-role \
          --instance_profile aws-elasticbeanstalk-ec2-role

wait_for_environment_ready "4. Waiting for environment to become ready..."

echo ""
echo "5. Increasing EB deployment timeouts for long worker setup..."
aws elasticbeanstalk update-environment \
        --environment-name $ENV_NAME \
        --region $REGION \
        --option-settings Namespace=aws:elasticbeanstalk:command,OptionName=Timeout,Value=$DEPLOYMENT_COMMAND_TIMEOUT Namespace=aws:autoscaling:launchconfiguration,OptionName=RootVolumeSize,Value=$ROOT_VOLUME_SIZE \
        --no-cli-pager >/dev/null

wait_for_environment_ready "6. Waiting for timeout setting to apply..."

echo ""
echo "7. Deploying app to EB..."

eb deploy $ENV_NAME \
         --archive $VERSION \
         --region $REGION

echo ""
echo "8. Configuring for basic health monitoring..."
aws elasticbeanstalk update-environment \
        --environment-name $ENV_NAME \
        --region $REGION \
        --option-settings Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=basic \
        --no-cli-pager >/dev/null

wait_for_environment_ready "9. Waiting for health monitoring update to complete..."

echo ""
echo "Done! You can use 'eb status' to check status of web service."
echo ""
