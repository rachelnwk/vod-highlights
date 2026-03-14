//
// API function: post /vods/presign
//
// Creates a presigned S3 URL for direct browser upload.
//

const { v4: uuidv4 } = require('uuid');
const { PutObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const { s3Client, env } = require('./config');

const ALLOWED_EXTENSIONS = new Set(['.mp4', '.mov', '.mkv']);
const MAX_UPLOAD_MB = Math.round(env.MAX_UPLOAD_BYTES / (1024 * 1024));

function getExtension(filename) {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot < 0) {
    return '';
  }
  return filename.slice(lastDot).toLowerCase();
}

function buildUploadKey(filename) {
  const clean = filename.replace(/[^a-zA-Z0-9._-]/g, '_');
  return `uploads/${Date.now()}-${uuidv4()}-${clean}`;
}

/**
 * post_vod_presign:
 *
 * @description returns { uploadUrl, s3Key } for client-side upload.
 */
exports.post_vod_presign = async (request, response, next) => {
  try {
    console.log('**Call to post /vods/presign...');

    const { filename, contentType } = request.body;
    const fileSizeBytes = Number(request.body?.fileSizeBytes || 0);
    const extension = getExtension(filename || '');
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return response.status(400).json({ error: 'Only .mp4, .mov, and .mkv files are allowed.' });
    }
    if (!Number.isFinite(fileSizeBytes) || fileSizeBytes <= 0) {
      return response.status(400).json({ error: 'A valid file size is required.' });
    }
    if (fileSizeBytes > env.MAX_UPLOAD_BYTES) {
      return response.status(400).json({ error: `Uploads must be ${MAX_UPLOAD_MB} MB or smaller.` });
    }

    const s3Key = buildUploadKey(filename);
    const uploadUrl = await getSignedUrl(
      s3Client,
      new PutObjectCommand({
        Bucket: env.AWS_S3_BUCKET,
        Key: s3Key,
        ...(contentType ? { ContentType: contentType } : {}),
      }),
      { expiresIn: 900 }
    );

    console.log('sending response...');
    response.json({ uploadUrl, s3Key });
  } catch (err) {
    console.log('ERROR:');
    console.log(err.message);
    next(err);
  }
};
