//
// API function: get /videos/:videoId/clips
//
// Returns generated highlight clips for a processed video.
//

const { pool } = require('./config');

/**
 * get_video_clips:
 *
 * @description returns all clip records mapped for frontend playback.
 */
exports.get_video_clips = async (request, response, next) => {
  try {
    console.log('**Call to get /videos/:videoId/clips...');

    const videoId = Number(request.params.videoId);
    if (Number.isNaN(videoId)) {
      return response.status(400).json({ error: 'Invalid videoId' });
    }

    const [clips] = await pool.execute(
      `SELECT id, start_time, end_time, score, clip_s3_key, thumbnail_s3_key
       FROM clips
       WHERE video_id = ?
       ORDER BY score DESC, start_time ASC`,
      [videoId]
    );
    console.log('sending response...');
    response.json(
      clips.map((clip) => ({
        clipId: clip.id,
        startTime: Number(clip.start_time),
        endTime: Number(clip.end_time),
        score: clip.score,
        clipKey: clip.clip_s3_key,
        thumbnailKey: clip.thumbnail_s3_key,
      }))
    );
  } catch (err) {
    console.log('ERROR:');
    console.log(err.message);
    next(err);
  }
};
