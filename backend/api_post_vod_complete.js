//
// API function: post /vods/complete
//
// Saves video/job rows and enqueues processing work on SQS.
//

const { HeadObjectCommand } = require('@aws-sdk/client-s3');
const { SendMessageCommand } = require('@aws-sdk/client-sqs');
const { pool, sqsClient, s3Client, env } = require('./config');

const ALLOWED_EXTENSIONS = new Set(['.mp4', '.mov', '.mkv']);
const MAX_UPLOAD_MB = Math.round(env.MAX_UPLOAD_BYTES / (1024 * 1024));

function getExtension(filename) {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot < 0) {
    return '';
  }
  return filename.slice(lastDot).toLowerCase();
}

/**
 * post_vod_complete:
 *
 * @description persists uploaded video metadata and queues processing.
 */
exports.post_vod_complete = async (request, response, next) => {
  try {
    console.log('**Call to post /vods/complete...');

    const { originalFilename, s3Key, playerName } = request.body;
    const extension = getExtension(originalFilename || '');
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return response.status(400).json({ error: 'Only .mp4, .mov, and .mkv files are allowed.' });
    }

    let uploadedObject;
    try {
      uploadedObject = await s3Client.send(
        new HeadObjectCommand({
          Bucket: env.AWS_S3_BUCKET,
          Key: s3Key,
        })
      );
    } catch {
      return response.status(400).json({ error: 'Uploaded video not found in S3.' });
    }

    const uploadedSizeBytes = Number(uploadedObject?.ContentLength || 0);
    if (!Number.isFinite(uploadedSizeBytes) || uploadedSizeBytes <= 0) {
      return response.status(400).json({ error: 'Uploaded video is empty or unreadable.' });
    }
    if (uploadedSizeBytes > env.MAX_UPLOAD_BYTES) {
      return response.status(400).json({ error: `Uploads must be ${MAX_UPLOAD_MB} MB or smaller.` });
    }

    const connection = await pool.getConnection();
    let videoId;
    let jobId;

    try {
      await connection.beginTransaction();

      const [videoResult] = await connection.execute(
        `INSERT INTO videos (original_filename, s3_key, player_name, status)
         VALUES (?, ?, ?, ?)`,
        [originalFilename, s3Key, playerName, 'queued']
      );
      videoId = videoResult.insertId;

      const [jobResult] = await connection.execute(
        `INSERT INTO jobs (video_id, status) VALUES (?, ?)`,
        [videoId, 'queued']
      );
      jobId = jobResult.insertId;

      await connection.commit();
    } catch (dbError) {
      await connection.rollback();
      throw dbError;
    } finally {
      connection.release();
    }

    await sqsClient.send(
      new SendMessageCommand({
        QueueUrl: env.AWS_SQS_QUEUE_URL,
        MessageBody: JSON.stringify({
          version: 1,
          type: 'process_vod',
          payload: {
            jobId,
            videoId,
            s3Key,
            playerName,
            originalFilename,
          },
        }),
      })
    );

    console.log('sending response...');
    response.status(201).json({ videoId, jobId, status: 'queued' });
  } catch (err) {
    console.log('ERROR:');
    console.log(err.message);
    next(err);
  }
};
