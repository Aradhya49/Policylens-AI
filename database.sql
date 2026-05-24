-- PolicyLens AI - Full Database Schema
-- Run this entire file once to set up the database from scratch

CREATE DATABASE IF NOT EXISTS policylens_db;
USE policylens_db;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(100)  NOT NULL UNIQUE,
    email           VARCHAR(150)  NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    profile_picture VARCHAR(255)  DEFAULT NULL,
    created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- Uploaded Documents Table
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,
    title       VARCHAR(255) NOT NULL,
    filename    VARCHAR(255) NOT NULL,
    category    VARCHAR(100) NOT NULL,
    file_size   INT          DEFAULT 0,
    uploaded_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- AI Analyses Table
CREATE TABLE IF NOT EXISTS ai_analyses (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    document_id          INT  NOT NULL,
    user_id              INT  NOT NULL,
    summary              TEXT,
    simplified_explanation TEXT,
    risk_level           ENUM('Low','Medium','High') DEFAULT 'Low',
    key_clauses          TEXT,
    risk_highlights      TEXT,
    analyzed_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES uploaded_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)     REFERENCES users(id)              ON DELETE CASCADE
);
