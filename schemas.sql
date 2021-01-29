CREATE TABLE IF NOT EXISTS todos (
    user_id bigint PRIMARY KEY,
    tasks text[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS errors (
    err_num    SERIAL,
    traceback  text,
    message    text,
    command    text
    );

CREATE TABLE IF NOT EXISTS guild_info (
    guild_id bigint PRIMARY KEY,
    prefixes text[] DEFAULT '{}'
    );

CREATE TABLE IF NOT EXISTS command_stats (
    date date,
    commands text,
    users text
)
