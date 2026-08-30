-- Migration: add missing performance indexes (MySQL-compatible)
-- MySQL does not support CREATE INDEX IF NOT EXISTS, so each index is
-- created only when it does not already exist.

SET @schema = DATABASE();

SET @sql := NULL;
SELECT CONCAT(
    'CREATE INDEX idx_lost_items_created ON lost_items(created_at)')
    INTO @sql
FROM information_schema.statistics
WHERE table_schema = @schema AND table_name = 'lost_items' AND index_name = 'idx_lost_items_created'
HAVING COUNT(*) = 0;
SET @sql := IFNULL(@sql, 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := NULL;
SELECT CONCAT(
    'CREATE INDEX idx_found_items_created ON found_items(created_at)')
    INTO @sql
FROM information_schema.statistics
WHERE table_schema = @schema AND table_name = 'found_items' AND index_name = 'idx_found_items_created'
HAVING COUNT(*) = 0;
SET @sql := IFNULL(@sql, 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := NULL;
SELECT CONCAT(
    'CREATE INDEX idx_matches_created ON matches(created_at)')
    INTO @sql
FROM information_schema.statistics
WHERE table_schema = @schema AND table_name = 'matches' AND index_name = 'idx_matches_created'
HAVING COUNT(*) = 0;
SET @sql := IFNULL(@sql, 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := NULL;
SELECT CONCAT(
    'CREATE INDEX idx_notifications_created ON notifications(created_at)')
    INTO @sql
FROM information_schema.statistics
WHERE table_schema = @schema AND table_name = 'notifications' AND index_name = 'idx_notifications_created'
HAVING COUNT(*) = 0;
SET @sql := IFNULL(@sql, 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := NULL;
SELECT CONCAT(
    'CREATE INDEX idx_activity_logs_created ON activity_logs(created_at)')
    INTO @sql
FROM information_schema.statistics
WHERE table_schema = @schema AND table_name = 'activity_logs' AND index_name = 'idx_activity_logs_created'
HAVING COUNT(*) = 0;
SET @sql := IFNULL(@sql, 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
