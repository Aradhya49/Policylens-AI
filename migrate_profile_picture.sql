-- Run this in MySQL to add profile_picture column to users table
USE policylens_db;

ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_picture VARCHAR(255) DEFAULT NULL;
