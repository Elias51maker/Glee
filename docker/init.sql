-- Glee Database Schema
-- Review sessions and iterations storage

CREATE TABLE IF NOT EXISTS review_sessions (
  id VARCHAR(36) PRIMARY KEY,
  project_path VARCHAR(512) NOT NULL,
  claude_session_id VARCHAR(36),
  files JSON NOT NULL,
  iteration INT NOT NULL DEFAULT 0,
  max_iterations INT NOT NULL DEFAULT 10,
  status ENUM('in_progress', 'approved', 'max_iterations', 'aborted', 'needs_human') NOT NULL DEFAULT 'in_progress',
  pending_questions JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_iterations (
  id VARCHAR(36) PRIMARY KEY,
  session_id VARCHAR(36) NOT NULL,
  iteration INT NOT NULL,
  codex_feedback TEXT,
  claude_changes TEXT,
  human_answers JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES review_sessions(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX idx_sessions_project ON review_sessions(project_path);
CREATE INDEX idx_sessions_status ON review_sessions(status);
CREATE INDEX idx_sessions_created ON review_sessions(created_at);
CREATE INDEX idx_iterations_session ON review_iterations(session_id);
CREATE FULLTEXT INDEX idx_iterations_feedback ON review_iterations(codex_feedback);
