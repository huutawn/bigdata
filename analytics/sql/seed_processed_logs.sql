INSERT INTO processed_logs VALUES
    ('v2', now(), 'req-000001', 'sess-bot-001', '1.2.3.4', 'Googlebot/2.1', 'GET', '/api/v1/products', '/api/v1/products', 404, 95, 0.91, 1, 74, 0.08, 0),
    ('v2', now(), 'req-000002', 'sess-user-002', '192.168.1.10', 'Mozilla/5.0', 'POST', '/api/v1/orders', '/api/v1/orders', 500, 3200, 0.12, 0, 74, 0.92, 1),
    ('v2', now(), 'req-000003', 'sess-user-003', '192.168.1.11', 'Mozilla/5.0 (Mobile)', 'GET', '/api/v1/login', '/api/v1/login', 200, 140, 0.03, 0, 61, 0.04, 0);

INSERT INTO bot_feature_windows VALUES
    (now() - 60, now(), '1.2.3.4', 'sess-bot-001', 'Googlebot/2.1', 42, 0.83, 12, 0.18, 0.04, 0.91, 1, 'mock-bot-v2'),
    (now() - 60, now(), '192.168.1.10', 'sess-user-002', 'Mozilla/5.0', 9, 0.22, 3, 0.00, 0.11, 0.12, 0, 'mock-bot-v2');

INSERT INTO load_forecasts VALUES
    (now(), 'system', '', 10, 55, 74, 'mock-forecast-v2'),
    (now(), 'endpoint', '/api/v1/products', 10, 24, 31, 'mock-forecast-v2');

INSERT INTO anomaly_alerts VALUES
    (now() - 60, now(), '/api/v1/orders', 17, 420.0, 1800.0, 3200.0, 0.12, 180.0, 0.92, 1, 'mock-anomaly-v2'),
    (now() - 60, now(), '/api/v1/login', 12, 120.0, 180.0, 220.0, 0.00, 110.0, 0.05, 0, 'mock-anomaly-v2');
