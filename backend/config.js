const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const { S3Client } = require('@aws-sdk/client-s3');
const { SQSClient } = require('@aws-sdk/client-sqs');

const defaultIniPaths = [
  path.join(__dirname, 'highlights-config.ini'),
];

function parseIni(content) {
  const values = {};
  let currentSection = null;

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || line.startsWith(';')) {
      continue;
    }

    if (line.startsWith('[') && line.endsWith(']')) {
      currentSection = line.slice(1, -1).trim().toLowerCase();
      continue;
    }

    const equalsAt = line.indexOf('=');
    if (equalsAt <= 0) {
      continue;
    }

    const key = line.slice(0, equalsAt).trim();
    const value = line.slice(equalsAt + 1).trim();
    if (currentSection) {
      values[`${currentSection}.${key}`] = value;
      if (key.toUpperCase() === key) {
        values[key] = value;
      }
      continue;
    }

    values[key] = value;
  }

  return values;
}

function getIniPaths() {
  const explicitPath = process.env.HIGHLIGHTS_CONFIG_PATH;
  const resolvedExplicitPath = explicitPath
    ? path.resolve(process.cwd(), explicitPath)
    : null;

  return resolvedExplicitPath ? [...defaultIniPaths, resolvedExplicitPath] : defaultIniPaths;
}

function readIniValues() {
  const mergedValues = {};

  for (const currentPath of getIniPaths()) {
    try {
      const content = fs.readFileSync(currentPath, 'utf8');
      Object.assign(mergedValues, parseIni(content));
    } catch {
      // Ignore missing optional config files.
    }
  }

  return mergedValues;
}

function required(values, name) {
  const value = values[name];
  if (!value) {
    throw new Error(`Missing required configuration value: ${name}`);
  }
  return value;
}

function firstValue(values, keys, defaultValue) {
  for (const key of keys) {
    const value = values[key];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return value;
    }
  }
  return defaultValue;
}

function loadEnv() {
  const iniValues = readIniValues();
  const allValues = { ...iniValues, ...process.env };

  const mapped = {
    PORT: firstValue(allValues, ['PORT'], 4000),
    AWS_REGION: firstValue(allValues, ['AWS_REGION', 's3.region_name', 'rds.region_name']),
    AWS_S3_BUCKET: firstValue(allValues, ['AWS_S3_BUCKET', 's3.bucket_name']),
    AWS_SQS_QUEUE_URL: firstValue(allValues, ['AWS_SQS_QUEUE_URL', 'sqs.queue_url']),
    MAX_UPLOAD_BYTES: firstValue(allValues, ['MAX_UPLOAD_BYTES'], 300 * 1024 * 1024),
    DB_HOST: firstValue(allValues, ['DB_HOST', 'rds.endpoint']),
    DB_PORT: firstValue(allValues, ['DB_PORT', 'rds.port_number'], 3306),
    DB_USER: firstValue(allValues, ['DB_USER', 'rds.user_name']),
    DB_PASSWORD: firstValue(allValues, ['DB_PASSWORD', 'rds.user_pwd']),
    DB_NAME: firstValue(allValues, ['DB_NAME', 'rds.db_name']),
  };

  return {
    PORT: Number(mapped.PORT),
    AWS_REGION: required(mapped, 'AWS_REGION'),
    AWS_S3_BUCKET: required(mapped, 'AWS_S3_BUCKET'),
    AWS_SQS_QUEUE_URL: required(mapped, 'AWS_SQS_QUEUE_URL'),
    MAX_UPLOAD_BYTES: Number(mapped.MAX_UPLOAD_BYTES),
    DB_HOST: required(mapped, 'DB_HOST'),
    DB_PORT: Number(mapped.DB_PORT),
    DB_USER: required(mapped, 'DB_USER'),
    DB_PASSWORD: required(mapped, 'DB_PASSWORD'),
    DB_NAME: required(mapped, 'DB_NAME'),
  };
}

const env = loadEnv();

const web_service_port = env.PORT;
const response_page_size = 12;

const pool = mysql.createPool({
  host: env.DB_HOST,
  port: env.DB_PORT,
  user: env.DB_USER,
  password: env.DB_PASSWORD,
  database: env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
});

const s3Client = new S3Client({ region: env.AWS_REGION });
const sqsClient = new SQSClient({ region: env.AWS_REGION });

module.exports = {
  web_service_port,
  response_page_size,
  loadEnv,
  env,
  pool,
  s3Client,
  sqsClient,
};
