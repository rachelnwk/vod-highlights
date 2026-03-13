//
// API function: get /jobs/:jobId
//
// Returns the current status of a processing job.
//

const { pool } = require('./config');

/**
 * get_job:
 *
 * @description returns one job status row mapped for the frontend.
 */
exports.get_job = async (request, response, next) => {
  try {
    console.log('**Call to get /jobs/:jobId...');

    const jobId = Number(request.params.jobId);
    if (Number.isNaN(jobId)) {
      return response.status(400).json({ error: 'Invalid jobId' });
    }

    const [rows] = await pool.execute(`SELECT * FROM jobs WHERE id = ?`, [jobId]);
    const job = rows[0] || null;
    if (!job) {
      return response.status(404).json({ error: 'Job not found' });
    }

    console.log('sending response...');
    response.json({
      jobId: job.id,
      videoId: job.video_id,
      status: job.status,
      errorMessage: job.error_message,
    });
  } catch (err) {
    console.log('ERROR:');
    console.log(err.message);
    next(err);
  }
};
