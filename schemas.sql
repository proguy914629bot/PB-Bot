CREATE TABLE IF NOT EXISTS todos (
    user_id bigint PRIMARY KEY,
    tasks text[] DEFAULT '{}'
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
    guild_prefixes text[]
    );

CREATE TABLE IF NOT EXISTS command_stats (
    date date,
    commands text,
    users text
)
