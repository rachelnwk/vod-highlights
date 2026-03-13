//
// VOD Highlights web service based on Node.js and Express. This file
// contains startup code and route registration.
//

const express = require('express');
const cors = require('cors');
const config = require('./config.js');
const getPingFile = require('./api_get_ping');
const postVodPresignFile = require('./api_post_vod_presign');
const postVodCompleteFile = require('./api_post_vod_complete');
const getJobFile = require('./api_get_job');
const getVideoClipsFile = require('./api_get_video_clips');

const app = express();

app.use(cors());
app.use(express.json({ limit: '2mb' }));

function validateBody(requiredFields) {
  return (req, res, next) => {
    for (const field of requiredFields) {
      if (req.body?.[field] === undefined || req.body[field] === null || req.body[field] === '') {
        return res.status(400).json({ error: `Missing required field: ${field}` });
      }
    }
    next();
  };
}

function getHealth(req, res) {
  res.json({
    status: 'ok',
    service: 'backend',
    uptime_in_secs: Math.round(process.uptime()),
    timestamp: new Date().toISOString(),
  });
}

app.get('/', getHealth);
app.get('/health', getHealth);
app.get('/ping', getPingFile.get_ping);

app.post('/vods/presign', validateBody(['filename']), postVodPresignFile.post_vod_presign);
app.post(
  '/vods/complete',
  validateBody(['originalFilename', 's3Key', 'playerName']),
  postVodCompleteFile.post_vod_complete
);

app.get('/jobs/:jobId', getJobFile.get_job);
app.get('/videos/:videoId/clips', getVideoClipsFile.get_video_clips);

app.use((error, req, res, next) => {
  console.error(
    `[ERROR] route=${req?.method || 'n/a'} ${req?.originalUrl || 'n/a'}`,
    error?.stack || error
  );
  res.status(500).json({
    error: error.message || 'Internal server error',
  });
});

app.listen(config.web_service_port, () => {
  console.log(`**Web service running, listening on port ${config.web_service_port}...`);
});
