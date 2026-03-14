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
const LOCAL_HELPER_BASE =
  config.VITE_LOCAL_HELPER_BASE_URL ||
  config.LOCAL_HELPER_BASE_URL ||
  config['client.local_helper'] ||
  config['client.webservice'] ||
  'http://localhost:4001';

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
  const url = `${LOCAL_HELPER_BASE}${path}`;

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
    throw new Error(`Failed to reach the local helper at ${LOCAL_HELPER_BASE}: ${lastError.message}`);
  }

  throw new Error(`Request failed for ${operation}`);
}

export function startLocalJob(file, playerName, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${LOCAL_HELPER_BASE}/jobs`);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onProgress) {
        return;
      }
      onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onerror = () => {
      reject(new Error(`Could not reach the local helper at ${LOCAL_HELPER_BASE}. Is it running?`));
    };

    xhr.onload = () => {
      let payload = {};
      try {
        payload = JSON.parse(xhr.responseText || '{}');
      } catch {
        payload = {};
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        if (onProgress) {
          onProgress(100);
        }
        resolve(payload);
        return;
      }

      reject(
        new Error(
          payload.error ||
            `Failed to start the local job (status ${xhr.status}).`
        )
      );
    };

    const formData = new FormData();
    formData.append('file', file);
    formData.append('playerName', playerName);
    xhr.send(formData);
  });
}

export async function getJobStatus(jobId) {
  return requestWithRetry(`/jobs/${jobId}`, {}, 'getJobStatus');
}

export async function getClipsForVideo(videoId) {
  return requestWithRetry(`/videos/${videoId}/clips`, {}, 'getClipsForVideo');
}

export function getConfiguredLocalHelper() {
  return LOCAL_HELPER_BASE;
}
