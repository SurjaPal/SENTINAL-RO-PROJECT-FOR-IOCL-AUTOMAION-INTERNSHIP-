CREATE TABLE IF NOT EXISTS chat_memory (
    id SERIAL PRIMARY KEY,
    time TIMESTAMPTZ NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL
);

SELECT create_hypertable('chat_memory', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_chat_memory_session ON chat_memory(session_id, time DESC);
