-- 创建账单记录表
CREATE TABLE bill_records (
    id INT NOT NULL AUTO_INCREMENT,
    record_id VARCHAR(50) UNIQUE,
    payment_method VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'CNY',
    transaction_time DATETIME NOT NULL,
    product_type VARCHAR(100) NOT NULL,
    merchant VARCHAR(200),
    description TEXT,
    image_path VARCHAR(500),
    ocr_text TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  	created_by VARCHAR(20) default '000000',
    PRIMARY KEY (id),
    INDEX idx_record_id (record_id),
    INDEX idx_transaction_time (transaction_time),
    INDEX idx_payment_method (payment_method)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;