import clientIniText from '../client-config.ini?raw';

// Purpose: Parse the frontend INI config into a flat key/value object.
// Input: content (string) containing raw INI text.
// Output: Object with parsed config values.
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
const MERGE_REQUEST_TIMEOUT_MS = 120000;

// Purpose: Pause between retry attempts.
// Input: ms (number) delay in milliseconds.
// Output: Promise that resolves after the delay.
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Purpose: Decide whether a failed request should be retried.
// Input: error (Error | null) and response (Response | undefined).
// Output: Boolean indicating whether another attempt should run.
function shouldRetry(error, response) {
  if (error) {
    return true;
  }

  if (!response) {
    return false;
  }

  return response.status >= 500;
}

// Purpose: Convert a fetch response into JSON or raise a readable frontend error.
// Input: response (Response) from fetch.
// Output: Promise resolving to parsed JSON data.
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

// Purpose: Send a request to the worker with timeout and retry logic.
// Input: path (string), options (object), and operation (string) for error labeling.
// Output: Promise resolving to parsed JSON from the worker.
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

// Purpose: Upload a local video to the worker and create a new processing job.
// Input: file (File), playerName (string), and onProgress (function | undefined).
// Output: Promise resolving to the created job payload.
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

// Purpose: Fetch the saved video library from the worker.
// Input: No arguments.
// Output: Promise resolving to the worker's video payload.
export async function listVideos() {
  return requestWithRetry('/videos', {}, 'listVideos');
}

// Purpose: Discard one saved clip from a specific video.
// Input: videoId (string) and clipId (string).
// Output: Promise resolving to the worker's delete response.
export async function discardClip(videoId, clipId) {
  return requestWithRetry(
    `/videos/${videoId}/clips/${clipId}`,
    { method: 'DELETE' },
    'discardClip'
  );
}

// Purpose: Delete all saved videos and clips from the worker-backed library.
// Input: No arguments.
// Output: Promise resolving to the worker's bulk-delete response.
export async function deleteAllVideos() {
  return requestWithRetry(
    '/videos',
    { method: 'DELETE' },
    'deleteAllVideos'
  );
}

// Purpose: Request one merged download for a list of selected clip IDs.
// Input: clipIds (string[]) in the desired merge order.
// Output: Promise that resolves after the browser download is triggered.
export async function downloadMergedClips(clipIds) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), MERGE_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${LOCAL_HELPER_BASE}/clips/merge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ clipIds }),
      signal: controller.signal,
    });

    if (!response.ok) {
      let message = 'Failed to merge selected clips.';
      try {
        const payload = await response.json();
        message = payload.error || message;
      } catch {
        // Ignore parse errors and fall back to the generic error.
      }
      throw new Error(message);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename=\"?([^"]+)\"?/i);
    const filename = match?.[1] || 'merged-library.mp4';

    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    throw new Error(`Failed to merge selected clips: ${error.message}`);
  } finally {
    clearTimeout(timeout);
  }
}

// Purpose: Expose the configured worker base URL to other frontend code.
// Input: No arguments.
// Output: String containing the current worker base URL.
export function getConfiguredLocalHelper() {
  return LOCAL_HELPER_BASE;
}
