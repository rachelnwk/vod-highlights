//
// API function: post /vods/complete
//
// Saves video/job rows and enqueues processing work on SQS.
//

const { SendMessageCommand } = require('@aws-sdk/client-sqs');
const { pool, sqsClient, env } = require('./config');

/**
 * post_vod_complete:
 *
 * @description persists uploaded video metadata and queues processing.
 */
exports.post_vod_complete = async (request, response, next) => {
  try {
    console.log('**Call to post /vods/complete...');

    const { originalFilename, s3Key, playerName } = request.body;
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
