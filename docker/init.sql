-- Creates the demo database alongside the main one.
-- Runs once when the postgres container first initialises (fresh volume only).
CREATE DATABASE money_tracker_demo;
GRANT ALL PRIVILEGES ON DATABASE money_tracker_demo TO money_tracker;
