
-- Tables used for the `class` command.


-- Represents a class semester
CREATE TABLE IF NOT EXISTS ClassSemester
(
    semester_id     TEXT        PRIMARY KEY,            -- Ex: FA2022, SU2022, SP2022
    semester_name   TEXT        UNIQUE NOT NULL,        -- Ex: Fall 2022, Summer 2022, Spring 2022
    semester_start  TEXT        NOT NULL,               -- The start date of the semester minus 5 days (UTC).
    semester_end    TEXT        NOT NULL                -- The end date of the semester plus 5 days (UTC).
);


-- Represents a class channel
CREATE TABLE IF NOT EXISTS ClassChannel
(
    channel_id      INTEGER     PRIMARY KEY,            -- Discord Channel ID
    semester_id     TEXT        NOT NULL,               -- ClassSemester.semester_id FOREIGN KEY
    category_id     INTEGER     NOT NULL,               -- Discord category the channel was created in or moved to (by archival).
    class_role_id   INTEGER     NOT NULL,               -- Discord Role ID
    class_prefix    TEXT        NOT NULL,               -- Ex: CPSC, MATH, ENGR, etc.
    class_number    INTEGER     NOT NULL,               -- Ex: 1060, 1070, 2120, 2070, etc.
    post_message_id INTEGER,                            -- Discord Message ID
    class_professor TEXT        NOT NULL,               -- Ex: Dean, Widman, Sorber, etc.
    class_name      TEXT,                               -- Ex: Intro to OS, Programming Systems, Network Programming, etc.
    class_archived  BOOLEAN     NOT NULL DEFAULT False, -- Marks whether the class has been archived
    FOREIGN KEY (semester_id)
        REFERENCES ClassSemester (semester_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


-- Represents a class channel pin
CREATE TABLE IF NOT EXISTS ClassPin
(
    post_message_id     INTEGER,                            -- Discord Message ID
    channel_id          INTEGER     NOT NULL,               -- ClassChannel.channel_id FOREIGN KEY
    pin_owner           INTEGER     NOT NULL,               -- Discord User ID
    pin_pinned          BOOLEAN     NOT NULL DEFAULT False, -- Marks whether the message has been pinned
    PRIMARY KEY (post_message_id, channel_id),
    FOREIGN KEY (channel_id)
        REFERENCES ClassChannel (channel_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


-- Populate ClassSemester table, if the values do not exist.

-- The start and end dates have been adjusted approximately *5 DAYS* of additional time
-- before and after the start and end dates for preparation/final discussion.
-- Times formatted as UTC (5 AM UTC is 12 AM EST), ignore daylight savings time changes.
-- Start/end date times should NOT overlap.

INSERT OR IGNORE INTO ClassSemester(semester_id, semester_name, semester_start, semester_end) VALUES
    ('sp2023', 'Spring 2023',   '2023-01-06 05:00:00',  '2023-05-10 05:00:00'),
    ('su2023', 'Summer 2023',   '2023-05-11 05:00:00',  '2023-08-12 05:00:00'),
    ('fa2023', 'Fall 2023',     '2023-08-18 05:00:00',  '2023-12-20 05:00:00');
