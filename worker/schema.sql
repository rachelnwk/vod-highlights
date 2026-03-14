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
DROP TABLE IF EXISTS jobs;

CREATE TABLE jobs
(
    id                  bigint unsigned not null AUTO_INCREMENT,
    original_filename   varchar(255) not null,
    player_name         varchar(120) not null,
    status              enum('queued', 'processing', 'completed', 'failed') not null default 'queued',
    stage               varchar(64) not null default 'queued',
    progress_percent    int not null default 0,
    summary_json        longtext null,
    error_message       text null,
    created_at          timestamp not null default current_timestamp,
    finished_at         timestamp null default null,
    PRIMARY KEY         (id)
);

CREATE TABLE clips
(
    id                  bigint unsigned not null AUTO_INCREMENT,
    job_id              bigint unsigned not null,
    clip_index          int not null,
    start_time          decimal(10,3) not null,
    end_time            decimal(10,3) not null,
    score               int not null,
    clip_s3_key         varchar(1024) not null,
    thumbnail_s3_key    varchar(1024) not null,
    created_at          timestamp not null default current_timestamp,
    PRIMARY KEY         (id),
    CONSTRAINT fk_clips_job
        FOREIGN KEY (job_id) REFERENCES jobs(id)
        ON DELETE CASCADE,
    INDEX idx_clips_job_score (job_id, score)
);


--
-- Create ficticious user of vod_highlights database to limit access:
--
DROP USER IF EXISTS 'vod-read-write';

CREATE USER 'vod-read-write' IDENTIFIED BY 'def456!!';

GRANT SELECT, SHOW VIEW, INSERT, UPDATE, DELETE, DROP, CREATE, ALTER ON vod_highlights.*
    TO 'vod-read-write';

FLUSH PRIVILEGES;
