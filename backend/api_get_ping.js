//
// API function: get /ping
//
// Returns (M, N) where M = number of objects in the S3 bucket and
// N = number of videos in the database.
//

const { ListObjectsV2Command } = require('@aws-sdk/client-s3');
const { pool, s3Client, env } = require('./config');

/**
 * get_ping:
 *
 * @description returns service health summary with S3 and DB counts.
 */
exports.get_ping = async (request, response) => {
  let dbConn;

  try {
    console.log('**Call to get /ping...');

    const s3Result = await s3Client.send(
      new ListObjectsV2Command({
        Bucket: env.AWS_S3_BUCKET,
      })
    );

    dbConn = await pool.getConnection();
    const [rows] = await dbConn.query('SELECT count(id) AS num_videos FROM videos;');

    const M = Number(s3Result?.KeyCount || 0);
    const N = Number(rows?.[0]?.num_videos || 0);

    console.log('sending response...');

    response.json({
      message: 'success',
      M,
      N,
    });
  } catch (err) {
    console.log('ERROR:');
    console.log(err.message);

    response.status(500).json({
      message: err.message,
      M: -1,
      N: -1,
    });
  } finally {
    try {
      if (dbConn) {
        dbConn.release();
      }
    } catch {
      // ignore
    }
  }
};
