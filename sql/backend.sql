-- Schema only: no credentials, user records, or uploaded content.

-- Create a MySQL database first, then import this file into that database.

-- Existing installations are upgraded by backend/migrate_schedule.py or FastAPI startup.

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS course (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	name VARCHAR(50) NOT NULL COMMENT 'Course name',
	code VARCHAR(50) NOT NULL COMMENT 'Course code',
	description VARCHAR(255) NOT NULL COMMENT 'Course description',
	status INTEGER NOT NULL COMMENT 'Status: 0 = inactive, 1 = active',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	UNIQUE (code)
)COMMENT='Course information table' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS kb_documents (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	original_name VARCHAR(255) NOT NULL COMMENT 'Original filename',
	disk_name VARCHAR(255) NOT NULL COMMENT 'Stored filename',
	rel_path VARCHAR(512) NOT NULL COMMENT 'Path relative to data/kb',
	size INTEGER NOT NULL COMMENT 'Size in bytes',
	ext VARCHAR(20) NOT NULL COMMENT 'File extension',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	UNIQUE (original_name)
)COMMENT='Knowledge base documents' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS semesters (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	name VARCHAR(100) NOT NULL,
	first_monday DATE NOT NULL,
	total_weeks INTEGER NOT NULL,
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS study_plan (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	user_id INTEGER NOT NULL COMMENT 'User ID',
	content TEXT NOT NULL COMMENT 'Study plan content',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id)
)COMMENT='Study plan table' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	username VARCHAR(50) NOT NULL COMMENT 'Username',
	password VARCHAR(255) NOT NULL COMMENT 'Password',
	name VARCHAR(50) NOT NULL COMMENT 'Name',
	`role` VARCHAR(50) NOT NULL COMMENT 'Role: student = student, admin = administrator',
	email VARCHAR(50) COMMENT 'Email',
	phone VARCHAR(50) COMMENT 'Phone number',
	avatar VARCHAR(50) COMMENT 'Avatar',
	status INTEGER NOT NULL COMMENT 'Status: 0 = disabled, 1 = active',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	UNIQUE (username)
)COMMENT='User information table' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedule_rules (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	semester_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	course_id INTEGER NOT NULL,
	weekday INTEGER NOT NULL,
	start_week INTEGER NOT NULL,
	end_week INTEGER NOT NULL,
	start_period INTEGER NOT NULL,
	end_period INTEGER NOT NULL,
	location VARCHAR(100) NOT NULL,
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	CONSTRAINT uq_schedule_rule_pattern UNIQUE (semester_id, user_id, course_id, weekday, start_week, end_week, start_period, end_period),
	FOREIGN KEY(semester_id) REFERENCES semesters (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(course_id) REFERENCES course (id),
	KEY `ix_schedule_rules_semester_id` (`semester_id`),
	KEY `ix_schedule_rules_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS schedules (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	rule_id INTEGER,
	source_date DATE,
	start_period INTEGER,
	end_period INTEGER,
	is_exception BOOL NOT NULL DEFAULT false,
	is_cancelled BOOL NOT NULL DEFAULT false,
	user_id INTEGER NOT NULL COMMENT 'student ID',
	class_date DATE NOT NULL COMMENT 'course date',
	period VARCHAR(50) NOT NULL COMMENT 'course period',
	course_id INTEGER NOT NULL COMMENT 'course ID',
	location VARCHAR(100) COMMENT 'course location',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	CONSTRAINT fk_schedule_rule FOREIGN KEY(rule_id) REFERENCES schedule_rules (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(course_id) REFERENCES course (id),
	KEY `ix_schedule_student_date` (`user_id`, `class_date`),
	UNIQUE KEY `uq_schedule_rule_date` (`rule_id`, `class_date`),
	UNIQUE KEY `uq_schedule_rule_source` (`rule_id`, `source_date`)
)COMMENT='Class schedule table' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
