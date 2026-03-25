INSERT INTO processed_logs VALUES
    (now(), '192.168.1.1', '/api/v1/login', 120, 0, 100, 0),
    (now(), '1.2.3.4', '/api/v1/products', 50, 1, 100, 0),
    (now(), '192.168.1.5', '/api/v1/cart', 4500, 0, 100, 1);
