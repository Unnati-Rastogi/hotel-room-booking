-- ============================================================
--  Smart Hotel Booking System — Database Schema
--  50 Rooms · 5 Floors × 10 Rooms · Triggers · Indexes
-- ============================================================

CREATE DATABASE IF NOT EXISTS hotel_booking;
USE hotel_booking;

-- ──────────────────────────────────────────────────────────
--  TABLE: rooms
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rooms (
    room_id       INT AUTO_INCREMENT PRIMARY KEY,
    floor_number  TINYINT      NOT NULL,
    room_number   VARCHAR(10)  NOT NULL UNIQUE,
    room_type     ENUM('single','double','suite') NOT NULL,
    price         DECIMAL(10,2) NOT NULL,
    status        ENUM('available','booked') NOT NULL DEFAULT 'available',
    view_type     ENUM('sea','pool','garden','city') NOT NULL,
    smoking       ENUM('yes','no') NOT NULL DEFAULT 'no',
    balcony       ENUM('yes','no') NOT NULL DEFAULT 'no'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────
--  TABLE: customers
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    email       VARCHAR(180) NOT NULL UNIQUE,
    phone       VARCHAR(20)  NOT NULL,
    password    VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────
--  TABLE: bookings
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    booking_id   INT AUTO_INCREMENT PRIMARY KEY,
    customer_id  INT  NOT NULL,
    room_id      INT  NOT NULL,
    check_in     DATE NOT NULL,
    check_out    DATE NOT NULL,
    adults       INT  NOT NULL DEFAULT 1,
    children     INT  NOT NULL DEFAULT 0,
    breakfast_opt  BOOLEAN NOT NULL DEFAULT 0,
    breakfast_days INT  NOT NULL DEFAULT 0,
    booking_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_booking_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_booking_room     FOREIGN KEY (room_id)     REFERENCES rooms(room_id),
    CONSTRAINT chk_dates CHECK (check_out > check_in)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────
--  TABLE: payments
-- ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    payment_id     INT AUTO_INCREMENT PRIMARY KEY,
    booking_id     INT            NOT NULL,
    amount         DECIMAL(10,2)  NOT NULL,
    payment_status ENUM('success','failed') NOT NULL DEFAULT 'success',
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ──────────────────────────────────────────────────────────
--  TRIGGER: auto-mark room as booked after INSERT
-- ──────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_after_booking_insert;

DELIMITER $$
CREATE TRIGGER trg_after_booking_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
    UPDATE rooms
    SET    status = 'booked'
    WHERE  room_id = NEW.room_id;
END$$
DELIMITER ;

-- ──────────────────────────────────────────────────────────
--  INDEXES
-- ──────────────────────────────────────────────────────────
-- Indexes (using procedure for MySQL 5.7 compatibility)
DROP PROCEDURE IF EXISTS create_indexes;

DELIMITER $$
CREATE PROCEDURE create_indexes()
BEGIN
    -- idx_bookings_room_id
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name  = 'bookings'
          AND index_name  = 'idx_bookings_room_id'
    ) THEN
        CREATE INDEX idx_bookings_room_id ON bookings(room_id);
    END IF;

    -- idx_bookings_checkin_out
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name  = 'bookings'
          AND index_name  = 'idx_bookings_checkin_out'
    ) THEN
        CREATE INDEX idx_bookings_checkin_out ON bookings(check_in, check_out);
    END IF;

    -- idx_rooms_status
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name  = 'rooms'
          AND index_name  = 'idx_rooms_status'
    ) THEN
        CREATE INDEX idx_rooms_status ON rooms(status);
    END IF;

    -- idx_rooms_floor
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name  = 'rooms'
          AND index_name  = 'idx_rooms_floor'
    ) THEN
        CREATE INDEX idx_rooms_floor ON rooms(floor_number);
    END IF;
END$$
DELIMITER ;

CALL create_indexes();
DROP PROCEDURE IF EXISTS create_indexes;

-- ──────────────────────────────────────────────────────────
--  SAMPLE DATA: 50 rooms  (5 floors × 10 rooms each)
--  Floor 1 = 101-110  |  Floor 2 = 201-210  | … | Floor 5 = 501-510
--
--  Room types  : single (40%), double (40%), suite (20%)
--  View types  : sea, pool, garden, city  — distributed evenly
--  Prices      : single ₹2000, double ₹3500, suite ₹6500
--  Status      : mostly available, a few pre-booked for demo
-- ──────────────────────────────────────────────────────────
INSERT INTO rooms (floor_number, room_number, room_type, price, status, view_type, smoking, balcony) VALUES
-- ── FLOOR 1 ──────────────────────────────────────────────
(1, '101', 'single', 2000.00, 'available', 'garden', 'no',  'no'),
(1, '102', 'single', 2000.00, 'available', 'city',   'no',  'no'),
(1, '103', 'double', 3500.00, 'booked',    'pool',   'no',  'yes'),
(1, '104', 'double', 3500.00, 'available', 'garden', 'no',  'yes'),
(1, '105', 'single', 2000.00, 'available', 'city',   'yes', 'no'),
(1, '106', 'single', 2000.00, 'available', 'garden', 'no',  'no'),
(1, '107', 'double', 3500.00, 'available', 'city',   'no',  'yes'),
(1, '108', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(1, '109', 'single', 2000.00, 'booked',    'pool',   'no',  'no'),
(1, '110', 'double', 3500.00, 'available', 'sea',    'no',  'yes'),
-- ── FLOOR 2 ──────────────────────────────────────────────
(2, '201', 'single', 2000.00, 'available', 'city',   'no',  'no'),
(2, '202', 'double', 3500.00, 'available', 'pool',   'no',  'yes'),
(2, '203', 'single', 2000.00, 'booked',    'garden', 'yes', 'no'),
(2, '204', 'double', 3500.00, 'available', 'sea',    'no',  'yes'),
(2, '205', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(2, '206', 'single', 2000.00, 'available', 'city',   'no',  'no'),
(2, '207', 'double', 3500.00, 'available', 'pool',   'no',  'yes'),
(2, '208', 'single', 2000.00, 'available', 'garden', 'no',  'no'),
(2, '209', 'double', 3500.00, 'booked',    'city',   'no',  'yes'),
(2, '210', 'single', 2000.00, 'available', 'sea',    'no',  'no'),
-- ── FLOOR 3 ──────────────────────────────────────────────
(3, '301', 'double', 3500.00, 'available', 'sea',    'no',  'yes'),
(3, '302', 'single', 2000.00, 'available', 'pool',   'no',  'no'),
(3, '303', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(3, '304', 'single', 2000.00, 'available', 'city',   'yes', 'no'),
(3, '305', 'double', 3500.00, 'booked',    'garden', 'no',  'yes'),
(3, '306', 'double', 3500.00, 'available', 'pool',   'no',  'yes'),
(3, '307', 'single', 2000.00, 'available', 'city',   'no',  'no'),
(3, '308', 'single', 2000.00, 'available', 'sea',    'no',  'no'),
(3, '309', 'double', 3500.00, 'booked',    'pool',   'no',  'yes'),
(3, '310', 'suite',  6500.00, 'available', 'garden', 'no',  'yes'),
-- ── FLOOR 4 ──────────────────────────────────────────────
(4, '401', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(4, '402', 'double', 3500.00, 'booked',    'city',   'no',  'yes'),
(4, '403', 'single', 2000.00, 'available', 'pool',   'no',  'no'),
(4, '404', 'single', 2000.00, 'available', 'garden', 'no',  'no'),
(4, '405', 'double', 3500.00, 'available', 'sea',    'no',  'yes'),
(4, '406', 'single', 2000.00, 'available', 'city',   'yes', 'no'),
(4, '407', 'double', 3500.00, 'available', 'pool',   'no',  'yes'),
(4, '408', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(4, '409', 'single', 2000.00, 'available', 'garden', 'no',  'no'),
(4, '410', 'double', 3500.00, 'booked',    'city',   'no',  'yes'),
-- ── FLOOR 5 (penthouse level) ─────────────────────────────
(5, '501', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(5, '502', 'suite',  6500.00, 'booked',    'sea',    'no',  'yes'),
(5, '503', 'double', 3500.00, 'available', 'pool',   'no',  'yes'),
(5, '504', 'double', 3500.00, 'available', 'sea',    'no',  'yes'),
(5, '505', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(5, '506', 'double', 3500.00, 'available', 'garden', 'no',  'yes'),
(5, '507', 'suite',  6500.00, 'available', 'city',   'no',  'yes'),
(5, '508', 'double', 3500.00, 'available', 'pool',   'no',  'yes'),
(5, '509', 'suite',  6500.00, 'available', 'sea',    'no',  'yes'),
(5, '510', 'suite',  6500.00, 'available', 'sea',    'no',  'yes');
