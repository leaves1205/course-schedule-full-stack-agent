-- Schema only: no credentials, user records, or uploaded content.
-- Create a MySQL database first, then import this file into that database.
-- The FastAPI application can also create these tables on first startup.

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Course information table';

CREATE TABLE IF NOT EXISTS study_plan (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	user_id INTEGER NOT NULL COMMENT 'User ID',
	content TEXT NOT NULL COMMENT 'Study plan content',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Study plan table';

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User information table';

CREATE TABLE IF NOT EXISTS schedules (
	id INTEGER NOT NULL COMMENT 'Primary key ID' AUTO_INCREMENT,
	user_id INTEGER NOT NULL COMMENT 'student ID',
	class_date DATE NOT NULL COMMENT 'course date',
	period VARCHAR(50) NOT NULL COMMENT 'course period',
	course_id INTEGER NOT NULL COMMENT 'course ID',
	location VARCHAR(100) COMMENT 'course location',
	create_time DATETIME NOT NULL COMMENT 'Created at',
	update_time DATETIME NOT NULL COMMENT 'Updated at',
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(course_id) REFERENCES course (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Class schedule table';
