CREATE TABLE IF NOT EXISTS todolist (
task text
);

CREATE TABLE IF NOT EXISTS errors (
        err_num    SERIAL,
        traceback  text,
        author     text,
        author_id  text,
        channel    text,
        channel_id text,
        guild      text,
        guild_id   text,
        message    text,
        message_id text,
        command    text
        );

CREATE TABLE IF NOT EXISTS prefixes (
        guild_id bigint PRIMARY KEY,
        guild_prefixes text[] DEFAULT '{pb}'
        );