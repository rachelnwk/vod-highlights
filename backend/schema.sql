--
-- create the database:
--
USE sys;

DROP DATABASE IF EXISTS vod_highlights;
CREATE DATABASE vod_highlights;


--
-- now create the tables:
--
USE vod_highlights;

DROP TABLE IF EXISTS clips;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS videos;

CREATE TABLE videos
(
    id                  bigint unsigned not null AUTO_INCREMENT,
    original_filename   varchar(255) not null,
    s3_key              varchar(1024) not null,
    player_name         varchar(120) not null,
    status              enum('queued', 'processing', 'completed', 'failed') not null default 'queued',
    created_at          timestamp not null default current_timestamp,
    PRIMARY KEY         (id)
);

CREATE TABLE jobs
(
    id                  bigint unsigned not null AUTO_INCREMENT,
    video_id            bigint unsigned not null,
    status              enum('queued', 'processing', 'completed', 'failed') not null default 'queued',
    error_message       text null,
    created_at          timestamp not null default current_timestamp,
    finished_at         timestamp null default null,
    PRIMARY KEY         (id),
    CONSTRAINT fk_jobs_video
        FOREIGN KEY (video_id) REFERENCES videos(id)
        ON DELETE CASCADE,
    INDEX idx_jobs_video (video_id)
);

CREATE TABLE events
(
    id                  bigint unsigned not null AUTO_INCREMENT,
    video_id            bigint unsigned not null,
    timestamp_seconds   decimal(10,3) not null,
    confidence          decimal(5,2) not null default 0,
    event_group_id      int null,
    created_at          timestamp not null default current_timestamp,
    PRIMARY KEY         (id),
    CONSTRAINT fk_events_video
        FOREIGN KEY (video_id) REFERENCES videos(id)
        ON DELETE CASCADE,
    INDEX idx_events_video_ts (video_id, timestamp_seconds)
);

CREATE TABLE clips
(
    id                  bigint unsigned not null AUTO_INCREMENT,
    video_id            bigint unsigned not null,
    job_id              bigint unsigned not null,
    start_time          decimal(10,3) not null,
    end_time            decimal(10,3) not null,
    score               int not null,
    clip_s3_key         varchar(1024) not null,
    thumbnail_s3_key    varchar(1024) not null,
    created_at          timestamp not null default current_timestamp,
    PRIMARY KEY         (id),
    CONSTRAINT fk_clips_video
        FOREIGN KEY (video_id) REFERENCES videos(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_clips_job
        FOREIGN KEY (job_id) REFERENCES jobs(id)
        ON DELETE CASCADE,
    INDEX idx_clips_video_score (video_id, score)
);


--
-- Create ficticious user of vod_highlights database to limit access:
--
DROP USER IF EXISTS 'vod-read-write';

CREATE USER 'vod-read-write' IDENTIFIED BY 'def456!!';

GRANT SELECT, SHOW VIEW, INSERT, UPDATE, DELETE, DROP, CREATE, ALTER ON vod_highlights.*
    TO 'vod-read-write';

FLUSH PRIVILEGES;
