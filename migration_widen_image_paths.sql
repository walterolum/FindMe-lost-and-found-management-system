-- Migration: Widen image_path columns for Cloudinary URLs
ALTER TABLE lost_items MODIFY COLUMN image_path VARCHAR(512);
ALTER TABLE found_items MODIFY COLUMN image_path VARCHAR(512);
ALTER TABLE item_images MODIFY COLUMN image_path VARCHAR(512);
-- users.profile_image is already VARCHAR(500)
