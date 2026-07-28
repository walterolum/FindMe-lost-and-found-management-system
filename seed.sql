USE findme_db;

INSERT INTO roles (id, name, description) VALUES
(1, 'Student', 'University student'),
(2, 'Lecturer', 'University lecturer or staff'),
(3, 'Administrator', 'System administrator');

INSERT INTO faculties (id, name, description) VALUES
(1, 'Faculty of Computing and Information Technology', 'Computing and IT programs'),
(2, 'Faculty of Business and Management', 'Business and management programs'),
(3, 'Faculty of Health Sciences', 'Health sciences programs'),
(4, 'Faculty of Engineering', 'Engineering programs'),
(5, 'Faculty of Arts and Social Sciences', 'Arts and social sciences programs');

INSERT INTO courses (id, name, code, faculty_id) VALUES
(1, 'Bachelor of Science in Computer Science', 'BSCS', 1),
(2, 'Bachelor of Science in Information Technology', 'BSIT', 1),
(3, 'Bachelor of Business Administration', 'BBA', 2),
(4, 'Bachelor of Science in Nursing', 'BSN', 3),
(5, 'Bachelor of Engineering in Software Engineering', 'BSE', 4),
(6, 'Bachelor of Arts in Communication', 'BAComm', 5),
(7, 'Diploma in Business Administration', 'DBA', 2),
(8, 'Certificate in IT', 'CIT', 1);

INSERT INTO categories (id, name, description) VALUES
(1, 'Electronics', 'Electronic devices and accessories'),
(2, 'Documents', 'Important documents and papers'),
(3, 'Bags', 'Handbags, backpacks, and bags'),
(4, 'Wallets', 'Wallets and purses'),
(5, 'Keys', 'Keys and keychains'),
(6, 'Books', 'Textbooks and books'),
(7, 'Clothing', 'Apparel and clothing items'),
(8, 'Accessories', 'Watches, jewelry, and accessories'),
(9, 'IDs/Cards', 'Identification cards and access cards'),
(10, 'Money', 'Currency and financial items'),
(11, 'Other', 'Other items not listed above');

INSERT INTO locations (id, name, description) VALUES
(1, 'Main Campus', 'Main campus area'),
(2, 'Library', 'University library'),
(3, 'Library Entrance', 'Near the library main entrance'),
(4, 'Lecture Room', 'Lecture rooms building'),
(5, 'Laboratory', 'Science and computer laboratories'),
(6, 'Cafeteria', 'University cafeteria and dining area'),
(7, 'Parking Area', 'Vehicle parking area'),
(8, 'Hostel', 'Student hostels'),
(9, 'Administration Block', 'University administration building'),
(10, 'Faculty Office', 'Faculty offices'),
(11, 'Computer Lab', 'Computer laboratories'),
(12, 'Lecture Hall', 'Lecture halls'),
(13, 'Student Lounge', 'Student common areas'),
(14, 'Sports Area', 'Sports and recreation area'),
(15, 'Other', 'Other locations');

INSERT INTO users (id, full_name, email, phone, student_staff_id, password_hash, role_id, faculty_id, course_id, is_active, email_verified) VALUES
(1, 'System Admin', 'admin@cavendish.ac.ug', '+256770000001', 'ADM-001', '$2b$12$oJQujYMVUdV5cWv3uMHSZ.5qi0uXqotg0iSuPY1rnoKJGc6s7kwK6', 3, NULL, NULL, TRUE, TRUE),
(2, 'John Musinguzi', 'john.musinguzi@cavendish.ac.ug', '+256770100002', 'STU-2024001', '$2b$12$oJQujYMVUdV5cWv3uMHSZ.5qi0uXqotg0iSuPY1rnoKJGc6s7kwK6', 1, 1, 1, TRUE, TRUE),
(3, 'Sarah Nakamya', 'sarah.nakamya@cavendish.ac.ug', '+256770200003', 'STU-2024002', '$2b$12$oJQujYMVUdV5cWv3uMHSZ.5qi0uXqotg0iSuPY1rnoKJGc6s7kwK6', 1, 1, 2, TRUE, TRUE),
(4, 'Dr. Peter Okello', 'peter.okello@cavendish.ac.ug', '+256770300004', 'LCT-001', '$2b$12$oJQujYMVUdV5cWv3uMHSZ.5qi0uXqotg0iSuPY1rnoKJGc6s7kwK6', 2, NULL, NULL, TRUE, TRUE),
(5, 'Grace Tumusiime', 'grace.tumusiime@cavendish.ac.ug', '+256770400005', 'STU-2024003', '$2b$12$oJQujYMVUdV5cWv3uMHSZ.5qi0uXqotg0iSuPY1rnoKJGc6s7kwK6', 1, 2, 3, TRUE, TRUE);