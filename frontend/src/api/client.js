import clientIniText from '../../client-config.ini?raw';

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

    values[key] = value;
    if (currentSection) {
      values[`${currentSection}.${key}`] = value;
    }
  }

  return values;
}

const config = parseIni(clientIniText);
const API_BASE =
  config.VITE_API_BASE_URL ||
  config.API_BASE_URL ||
  config['client.webservice'] ||
  'http://localhost:4000';
const S3_BUCKET =
  config.VITE_S3_BUCKET ||
  config.AWS_S3_BUCKET ||
  config.bucket_name ||
  config['s3.bucket_name'] ||
  '';

const RETRY_ATTEMPTS = 3;
const RETRY_BASE_DELAY_MS = 500;
const REQUEST_TIMEOUT_MS = 10000;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function shouldRetry(error, response) {
  if (error) {
    return true;
  }

  if (!response) {
    return false;
  }

  return response.status >= 500;
}

async function handleResponse(response) {
  if (!response.ok) {
    let message = 'Request failed';
    try {
      const data = await response.json();
      message = data.error || message;
    } catch {
      // Ignore parse errors and use fallback message.
    }
    throw new Error(message);
  }
  return response.json();
}

async function requestWithRetry(path, options = {}, operation = 'request') {
  let lastError;
  const url = `${API_BASE}${path}`;

  for (let attempt = 1; attempt <= RETRY_ATTEMPTS; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (shouldRetry(null, response) && attempt < RETRY_ATTEMPTS) {
        const delay = RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
        console.warn(`[API] ${operation} retry ${attempt}/${RETRY_ATTEMPTS - 1} after ${response.status}`);
        await sleep(delay);
        continue;
      }

      return handleResponse(response);
    } catch (error) {
      clearTimeout(timeout);
      lastError = error;

      if (attempt < RETRY_ATTEMPTS) {
        const delay = RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
        console.warn(`[API] ${operation} network retry ${attempt}/${RETRY_ATTEMPTS - 1}`, error);
        await sleep(delay);
        continue;
      }
    }
  }

  if (lastError) {
    throw new Error(`Failed to reach API at ${API_BASE}: ${lastError.message}`);
  }

  throw new Error(`Request failed for ${operation}`);
}

export async function getPresignedUploadUrl(filename, contentType) {
  return requestWithRetry(
    '/vods/presign',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename, contentType }),
    },
    'getPresignedUploadUrl'
  );
}

export async function completeUpload(originalFilename, s3Key, playerName) {
  return requestWithRetry(
    '/vods/complete',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ originalFilename, s3Key, playerName }),
    },
    'completeUpload'
  );
}

export async function getJobStatus(jobId) {
  return requestWithRetry(`/jobs/${jobId}`, {}, 'getJobStatus');
}

export async function getClipsForVideo(videoId) {
  return requestWithRetry(`/videos/${videoId}/clips`, {}, 'getClipsForVideo');
}

export function getConfiguredBucket() {
  return S3_BUCKET;
}
