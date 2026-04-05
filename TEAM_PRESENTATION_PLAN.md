# Kế Hoạch Thuyết Trình Team 5 Người

## 1. Mục tiêu tài liệu

Tài liệu này dùng để chuẩn bị buổi thuyết trình cho team 5 người theo đúng mô hình ownership đã ghi trong repo:

- Tech Lead
- Thành viên 1: Generator owner
- Thành viên 2: Stream owner
- Thành viên 3: ML owner
- Thành viên 4: Analytics owner

Nội dung dưới đây được tổng hợp từ:

- `README.md`
- `docs/team-workflow.md`
- `docs.md`
- `CONTRACTS.md`
- `ML_HANDOFF_REPORT.md`
- Các artifact thực tế trong `generator/`, `stream-processor/`, `ml-api/`, `analytics/`, `contracts/`, `infra/`, `scripts/`, `tests/`

Lưu ý quan trọng khi trình bày:

- Ownership trong tài liệu đang rõ ràng và có thể dùng trực tiếp cho phân vai.
- Một số tài liệu cũ còn nhắc `NATS`, nhưng code và hạ tầng hiện tại của repo đang chạy với `Kafka`.
- Vì vậy khi thuyết trình, team nên thống nhất mô tả implementation hiện tại là:
  `generator -> Kafka -> stream-processor -> ml-api -> ClickHouse -> Grafana`

---

## 2. Thông điệp chính của bài thuyết trình

Thông điệp đội nên truyền tải:

`Đây là một pipeline AIOps local-first, xử lý log truy cập theo thời gian thực, biến log thô thành feature windows, gọi ML theo từng bài toán riêng, lưu kết quả vào ClickHouse và trực quan hóa trên Grafana.`

Ba ý quan trọng cần nhấn mạnh:

1. Dự án không gửi từng raw event sang một endpoint ML chung chung.
2. Stream processor tạo ra các `feature windows` theo ngữ nghĩa nghiệp vụ.
3. Mỗi nhiệm vụ ML là một contract riêng: bot detection, load forecasting, anomaly detection.

---

## 3. Mục tiêu buổi thuyết trình

Sau buổi thuyết trình, người nghe cần hiểu rõ:

1. Bài toán dự án giải quyết là gì.
2. Dữ liệu đi qua pipeline như thế nào.
3. Vì sao kiến trúc v2 tách raw logs, feature windows và predictions.
4. Mỗi thành viên phụ trách phần nào.
5. Team đã xây dựng được những gì thực tế trong repo.
6. Hệ thống đang mạnh ở đâu, còn hạn chế gì, và hướng cải thiện tiếp theo là gì.

---

## 4. Thời lượng đề xuất

Thời lượng phù hợp: `22-28 phút` + `5-7 phút Q&A`

Phân bổ đề xuất:

| Người trình bày | Thời lượng | Trọng tâm |
|---|---:|---|
| Tech Lead | 5 phút | Bối cảnh, kiến trúc, contracts, điều phối team |
| Thành viên 1 | 4 phút | Generator, synthetic traffic, replay log |
| Thành viên 2 | 6 phút | Stream processing, feature windows, fallback, checkpoint |
| Thành viên 3 | 5 phút | ML API, models, mock/model mode, datasets |
| Thành viên 4 | 4 phút | ClickHouse, dashboard, seed, smoke query, demo kết quả |
| Cả team | 5-7 phút | Demo ngắn + Q&A |

Nếu giảng viên hoặc hội đồng chỉ cho `15-18 phút`, hãy rút gọn bằng cách:

- Gộp phần kiến trúc và contracts vào phần mở đầu của Tech Lead.
- Cho Thành viên 4 trình bày dashboard thật nhanh, tập trung vào insight thay vì cấu hình.
- Chuyển phần “điểm yếu và hướng mở rộng” thành 1 slide duy nhất.

---

## 5. Kịch bản thuyết trình tổng thể

## 5.1 Storyline đề xuất

Thứ tự nên kể:

1. Vấn đề cần giải quyết.
2. Kiến trúc tổng thể.
3. Hợp đồng dữ liệu và nguyên tắc tách trách nhiệm.
4. Generator tạo dữ liệu gì và vì sao dữ liệu đó hữu ích.
5. Stream processor biến raw logs thành feature windows như thế nào.
6. ML API nhận payload gì, suy luận ra sao.
7. Analytics lưu và trực quan hóa kết quả như thế nào.
8. Team tổ chức làm việc ra sao để ghép các phần lại an toàn.
9. Demo hoặc mô phỏng dòng chảy end-to-end.
10. Kết luận, bài học và hướng phát triển.

## 5.2 Slide plan chi tiết

| Slide | Người nói | Thời lượng | Nội dung chính | Mục tiêu |
|---|---|---:|---|---|
| 1 | Tech Lead | 1 phút | Tên đề tài, mục tiêu AIOps, 3 bài toán ML | Mở bài rõ ràng |
| 2 | Tech Lead | 1 phút | Bài toán nghiệp vụ và lý do cần pipeline realtime | Tạo ngữ cảnh |
| 3 | Tech Lead | 1.5 phút | Kiến trúc tổng thể `generator -> Kafka -> stream -> ml-api -> ClickHouse -> Grafana` | Cho người nghe thấy toàn cảnh |
| 4 | Tech Lead | 1.5 phút | Contracts v2 và nguyên tắc `raw logs -> feature windows -> predictions` | Giải thích tư duy thiết kế |
| 5 | Thành viên 1 | 2 phút | Generator synthetic traffic | Giải thích nguồn dữ liệu giả lập |
| 6 | Thành viên 1 | 2 phút | Replay access logs thật, session synthesis, route inference | Chứng minh có khả năng replay dữ liệu thật |
| 7 | Thành viên 2 | 3 phút | Stream processing, cửa sổ bot/anomaly/forecast, state, checkpoint | Nêu phần kỹ thuật lõi |
| 8 | Thành viên 2 | 3 phút | ML integration, fallback chain, ClickHouse writing | Cho thấy hệ thống chịu lỗi tốt |
| 9 | Thành viên 3 | 2.5 phút | FastAPI, Pydantic contracts, 3 endpoint ML | Giải thích tầng suy luận |
| 10 | Thành viên 3 | 2.5 phút | Datasets, model thật, mock mode, guardrail | Chứng minh phần ML có cơ sở |
| 11 | Thành viên 4 | 2 phút | ClickHouse tables, seed, smoke queries | Chốt phần lưu trữ |
| 12 | Thành viên 4 | 2 phút | Grafana dashboard, insight chính, demo | Kết nối với góc nhìn vận hành |
| 13 | Tech Lead | 1 phút | Cách team chia việc, phối hợp, testing, CI | Chứng minh làm việc nhóm bài bản |
| 14 | Tech Lead | 1 phút | Điểm mạnh, hạn chế, hướng phát triển | Kết luận chuyên nghiệp |

---

## 6. Giải thích công nghệ theo cách dễ thuyết trình

## 6.1 Python 3.12

Vai trò:

- Là ngôn ngữ chính cho toàn bộ project.
- Dùng cho generator, stream processor, ML API, analytics scripts và test.

Khi trình bày nên nói:

`Nhóm chọn Python để giữ toàn bộ pipeline trong một hệ ngôn ngữ thống nhất, giúp việc trao đổi dữ liệu, kiểm thử và phối hợp giữa các thành viên đơn giản hơn.`

## 6.2 Kafka

Vai trò:

- Là message broker trung gian giữa `generator` và `stream-processor`.
- Topic chính là `logs.raw`.
- Giúp tách producer và consumer, tránh việc hai service phụ thuộc trực tiếp vào nhau.

Khi trình bày nên nói:

`Kafka giúp chúng em đệm dữ liệu ở giữa pipeline. Generator chỉ cần đẩy raw logs vào topic, còn stream processor có thể đọc theo batch và xử lý độc lập.`

Điểm nên nhấn mạnh:

- Hệ thống local đang dùng Kafka theo `infra/docker-compose.yml`.
- App local đọc cấu hình từ `KAFKA_BOOTSTRAP_SERVERS`.
- Producer dùng `kafka-python`.

## 6.3 Stream Processing

Vai trò:

- Chuyển dữ liệu từ mức event sang mức phân tích.
- Gom log theo cửa sổ thời gian và theo thực thể hoặc endpoint.
- Tạo feature windows phù hợp cho từng bài toán ML.

Khi trình bày nên nói:

`Điểm quan trọng nhất của kiến trúc v2 là stream processor không gửi raw logs sang ML. Nó phải tổng hợp thành những đặc trưng có ý nghĩa, ví dụ hành vi của một session, lịch sử tải gần đây hoặc baseline độ trễ của một endpoint.`

## 6.4 PySpark và Pure Python

Vai trò:

- Stream processor hỗ trợ cả hai cách build window.
- Mặc định có thể chạy bằng Python thuần.
- Có thể bật PySpark để mô phỏng cách xử lý dữ liệu theo hướng big data hơn.

Khi trình bày nên nói:

`Nhóm giữ hai đường cài đặt: một đường pure Python để local development đơn giản, và một đường PySpark để thể hiện hướng mở rộng sang xử lý dữ liệu lớn.`

## 6.5 FastAPI + Pydantic

Vai trò:

- Dùng để xây `ml-api`.
- Mỗi endpoint có request/response model rõ ràng.
- Tự động validate đầu vào.

Khi trình bày nên nói:

`FastAPI giúp bọn em định nghĩa rõ giao diện ML service, còn Pydantic giúp kiểm soát payload để stream gửi sang ML đúng format.`

## 6.6 scikit-learn + joblib

Vai trò:

- Dùng để load model thật cho bot, forecast và anomaly.
- Model artifacts được đặt trong `ml-api/models/`.

Khi trình bày nên nói:

`Phần ML không chỉ dừng ở mock logic. Repo hiện có các model `.joblib` thật và cấu hình tương ứng để suy luận cho ba bài toán.`

## 6.7 ClickHouse

Vai trò:

- Là nơi lưu `processed_logs`, `bot_feature_windows`, `load_forecasts`, `anomaly_alerts`.
- Phù hợp cho truy vấn phân tích theo thời gian, tốc độ cao.

Khi trình bày nên nói:

`ClickHouse là tầng phân tích của pipeline. Sau khi stream xử lý xong, các rows được đẩy vào ClickHouse để phục vụ dashboard và truy vấn phân tích.`

## 6.8 Grafana

Vai trò:

- Trực quan hóa dữ liệu từ ClickHouse.
- Dashboard chính là `analytics/grafana/dashboards/aiops-overview.json`.

Khi trình bày nên nói:

`Grafana là lớp cuối cùng để người vận hành quan sát hệ thống: traffic, forecast, bot entities và anomaly alerts.`

## 6.9 JSON Schema + Contracts

Vai trò:

- Bảo đảm các nhóm giao tiếp đúng payload.
- Tránh việc mỗi nhóm hiểu dữ liệu theo một kiểu khác nhau.

Khi trình bày nên nói:

`Contracts là xương sống của cách làm việc nhóm. Khi nhóm Generator, Stream, ML và Analytics làm song song, contracts giúp mọi người ghép module lại mà ít vỡ nhất.`

## 6.10 Docker Compose + Make + PowerShell + GitHub Actions

Vai trò:

- Docker Compose chạy hạ tầng dùng chung.
- Make và PowerShell giúp local run trên Linux và Windows.
- GitHub Actions hỗ trợ validate và test.

Khi trình bày nên nói:

`Nhóm xây workflow local-first: hạ tầng chạy bằng Docker, còn app service chạy trên host để dễ debug và phát triển.`

---

## 7. Giải thích kỹ kiến trúc nghiệp vụ

## 7.1 Dữ liệu đi như thế nào

Luồng chuẩn của dự án:

1. `generator` tạo raw logs hoặc replay access logs thật.
2. Log được gửi vào Kafka topic `logs.raw`.
3. `stream-processor` đọc log, chuẩn hóa dữ liệu, cập nhật runtime state.
4. Stream tạo 3 loại feature payload:
   - bot detection window
   - forecast request
   - anomaly detection window
5. Các payload này được gửi tới `ml-api`.
6. `ml-api` trả về prediction tương ứng.
7. `stream-processor` ghép prediction vào processed rows.
8. Dữ liệu được ghi vào ClickHouse.
9. Grafana đọc từ ClickHouse và hiển thị dashboard.

## 7.2 Ba bài toán ML trong dự án

### Bot Detection

Đầu vào:

- Nhóm theo `ip + session_id + user_agent`
- Cửa sổ `60 giây`, trượt `10 giây`

Feature chính:

- số request
- thời lượng
- thời gian trung bình
- tỷ lệ request lặp lại
- tỷ lệ 2xx, 3xx, 4xx, 5xx
- phân bố method
- cờ night
- max barrage

Đầu ra:

- `is_bot`
- `bot_score`

### Load Forecasting

Đầu vào:

- Bucket traffic `60 giây`
- Lịch sử `10 bucket`
- scope `system` hoặc `endpoint`

Feature chính:

- `history_rps`
- `rolling_mean_5`
- `rolling_std_5`
- `hour_of_day`
- `day_of_week`

Đầu ra:

- `predicted_request_count`

### Anomaly Detection

Đầu vào:

- Nhóm theo `endpoint`
- Cửa sổ `60 giây`, trượt `10 giây`
- baseline lookback `5 phút`

Feature chính:

- `request_count`
- `avg_latency_ms`
- `p95_latency_ms`
- `p99_latency_ms`
- `status_5xx_ratio`
- `baseline_avg_latency_ms`
- `baseline_5xx_ratio`

Đầu ra:

- `is_anomaly`
- `anomaly_score`

## 7.3 Tư duy thiết kế v2

Đây là điểm Tech Lead cần nhấn mạnh rất rõ:

- `Raw log` chỉ là dữ liệu sự kiện.
- `Feature window` mới là dữ liệu có nghĩa cho ML.
- `Prediction` là đầu ra nghiệp vụ.

Vì vậy:

- Generator không nên tự gán nhãn ML.
- ML API không nên nhận event thô.
- Stream processor là lớp chuyển đổi ngữ nghĩa quan trọng nhất.

---

## 8. Phân công chi tiết và phần trình bày của từng người

## 8.1 Tech Lead

### Ownership

- `infra/`
- `contracts/`
- `.github/`
- `docs/`
- top-level docs như `README.md`, `CONTRACTS.md`, `docs.md`
- điều phối merge vào `main`

### Những gì role này đã làm

1. Thiết kế kiến trúc v2 của toàn hệ thống.
2. Chia ranh giới rõ giữa Generator, Stream, ML và Analytics.
3. Định nghĩa luồng dữ liệu chuẩn:
   `raw logs -> feature windows -> predictions -> ClickHouse -> Grafana`
4. Xây tài liệu contracts làm nguồn sự thật duy nhất cho nhóm.
5. Chuẩn hóa schema và sample payload để các module tích hợp được với nhau.
6. Xây workflow nhóm:
   - ownership
   - branching
   - dependency matrix
   - PR checklist
7. Dựng hạ tầng dùng chung qua Docker Compose.
8. Thiết kế local-first workflow để các service app chạy trực tiếp trên host.
9. Tạo CI/CD cơ bản:
   - validate contracts
   - chạy unit tests
   - validate docker-compose
10. Viết tài liệu kiến trúc, local dev và testing.

### Artifact tiêu biểu để chứng minh

- `README.md`
- `CONTRACTS.md`
- `docs/team-workflow.md`
- `docs/v2-streaming-design.md`
- `docs/local-dev.md`
- `docs/linux-testing.md`
- `infra/docker-compose.yml`
- `scripts/validate_contracts.py`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `.github/pull_request_template.md`

### Khi đứng thuyết trình nên nói gì

`Phần em phụ trách là kiến trúc tổng thể, contracts và hạ tầng phối hợp nhóm. Em đảm bảo các module không chỉ chạy riêng lẻ mà còn giao tiếp đúng với nhau thông qua schema, example payload và quy trình validate.`

### 3 điểm nên nhấn mạnh

1. Team không chia việc theo cảm tính mà chia theo ownership rõ ràng.
2. Contracts giúp các thành viên làm song song mà vẫn ráp được hệ thống.
3. Hệ thống được tổ chức theo local-first để dễ phát triển và demo.

---

## 8.2 Thành viên 1: Generator Owner

### Ownership

- `generator/`

### Những gì role này đã làm

1. Xây generator log giả lập trong `generator/src/generator/main.py`.
2. Tạo traffic cycle `24 phase` để mô phỏng nhiều trạng thái hệ thống:
   - bot scraping
   - login probing
   - 5xx incidents
   - normal browsing
   - mobile behavior
   - admin activity
   - mixed traffic
3. Dùng seeded RNG để dữ liệu có tính tất định, thuận tiện test và demo.
4. Tạo load profile có biến thiên theo thời gian để không bị đều giả tạo.
5. Đẩy raw log vào Kafka topic `logs.raw`.
6. Xây module replay log thật trong `generator/src/generator/replay_access_logs.py`.
7. Hỗ trợ đọc nhiều nguồn log:
   - `.log`
   - `.txt`
   - `.gz`
   - thư mục chứa nhiều file
8. Parse log theo format Apache/Nginx combined log.
9. Chuẩn hóa endpoint, route template và latency heuristics.
10. Tự tổng hợp session bằng `Sessionizer` dựa trên IP, user-agent và khoảng cách thời gian.
11. Hỗ trợ time-scale compression để phát lại log nhanh hơn realtime.
12. Hỗ trợ flush có backoff để publish ổn định hơn.
13. Viết test cho tính tất định và replay behavior.

### Artifact tiêu biểu để chứng minh

- `generator/src/generator/main.py`
- `generator/src/generator/replay_access_logs.py`
- `generator/requirements.txt`
- `generator/Dockerfile`
- `tests/test_generator.py`

### Giá trị phần việc này mang lại

- Tạo dữ liệu synthetic để demo dù không có log thật.
- Cho phép replay access log thật để mô phỏng production-like input.
- Là nguồn đầu vào chuẩn cho toàn pipeline.

### Khi đứng thuyết trình nên nói gì

`Phần em phụ trách là tạo dữ liệu đầu vào cho hệ thống. Em xây hai hướng: một là generator mô phỏng traffic theo kịch bản có chủ đích, hai là replay access log thật để bám sát dữ liệu thực tế hơn.`

### Những điểm kỹ thuật nên kể ra

- 24-phase traffic model
- deterministic generation
- session synthesis
- route template inference
- gzip support
- Kafka publishing

---

## 8.3 Thành viên 2: Stream Owner

### Ownership

- `stream-processor/`

### Vai trò thực sự của Stream Owner trong hệ thống

Nếu nói ngắn gọn, Stream owner là người chịu trách nhiệm cho phần quan trọng nhất của pipeline:

- nhận raw logs từ Kafka
- biến raw logs thành dữ liệu có ngữ nghĩa phân tích
- xây feature windows cho từng bài toán ML
- gọi ML API hoặc fallback local mock
- biến prediction thành các hàng dữ liệu analytics
- ghi kết quả ra ClickHouse hoặc fallback file

Nói cách khác:

- Generator tạo dữ liệu đầu vào
- ML API trả dự đoán
- Analytics hiển thị dữ liệu
- còn Stream owner là người “nối” tất cả chúng lại thành một luồng xử lý hoàn chỉnh

Đây là role khó nhất về mặt luồng dữ liệu vì phải hiểu:

- contract đầu vào
- state trong bộ nhớ
- cửa sổ thời gian
- feature engineering
- gọi HTTP sang ML
- format ghi xuống ClickHouse
- các tình huống lỗi và fallback

### Những gì role này đã làm

1. Xây service xử lý trung tâm trong `stream-processor/src/stream_processor/main.py`.
2. Thiết kế `StreamSettings` để quản lý toàn bộ config vận hành.
3. Đọc dữ liệu từ Kafka theo batch qua `fetch_kafka_batch`.
4. Chuẩn hóa raw logs qua `normalize_raw_log`.
5. Xây cơ chế lưu trạng thái runtime bằng `RuntimeState`.
6. Cài checkpoint qua:
   - `save_checkpoint`
   - `load_checkpoint`
7. Duy trì `traffic_buckets` để phục vụ forecasting.
8. Duy trì `recent_events` để phục vụ bot/anomaly windows.
9. Xây hai đường xử lý cửa sổ:
   - `build_bot_feature_windows_python`
   - `build_bot_feature_windows_spark`
10. Xây tiếp hai đường cho anomaly:
   - `build_anomaly_feature_windows_python`
   - `build_anomaly_feature_windows_spark`
11. Xây logic forecast request qua `build_forecast_requests`.
12. Gọi `ml-api` qua HTTP và có timeout/ready check.
13. Tạo fallback nội bộ khi `ml-api` không sẵn sàng bằng `mock_analyzer.py`.
14. Chuyển prediction thành các row phục vụ analytics:
   - `build_processed_logs`
   - `build_bot_feature_rows`
   - `build_load_forecast_rows`
   - `build_anomaly_alert_rows`
15. Ghi dữ liệu vào ClickHouse.
16. Tạo fallback file output nếu ClickHouse lỗi.
17. Tạo fallback sample raw logs nếu Kafka không có dữ liệu.
18. Viết unit test cho bot window, forecast history, fallback path và tích hợp ML API.

### Giải thích rõ `StreamSettings` để làm gì

`StreamSettings` là object cấu hình trung tâm của stream processor.

Nó tồn tại để gom tất cả các biến môi trường và giá trị mặc định vào một chỗ duy nhất, thay vì rải config khắp code.

Nhờ đó Stream owner kiểm soát được:

- kết nối Kafka:
  - `bootstrap_servers`
  - `topic`
- cách poll dữ liệu:
  - `batch_size`
  - `poll_timeout_seconds`
  - `poll_interval_seconds`
- nơi gọi ML:
  - `ml_api_url`
  - `ml_timeout_seconds`
- nơi ghi analytics:
  - `clickhouse_url`
  - tên các bảng ClickHouse
- nơi fallback:
  - `raw_log_sample_path`
  - `fallback_output_path`
- cách build windows:
  - `bot_window_seconds`
  - `bot_window_slide_seconds`
  - `anomaly_window_seconds`
  - `anomaly_window_slide_seconds`
  - `anomaly_baseline_lookback_seconds`
  - `forecast_bucket_seconds`
  - `forecast_history_size`
- checkpoint:
  - `checkpoint_path`
  - `checkpoint_interval`

Ý nghĩa khi thuyết trình:

`StreamSettings` làm cho service có thể đổi môi trường chạy mà không cần sửa logic. Ví dụ đổi Kafka server, đổi ClickHouse URL, đổi kích thước cửa sổ hay đổi timeout chỉ cần thay config.

### Giải thích rõ `RuntimeState` để làm gì

`RuntimeState` là trạng thái đang sống của stream processor trong bộ nhớ.

Nó có 2 thành phần chính:

1. `recent_events`
2. `traffic_buckets`

#### `recent_events`

Đây là danh sách các raw log đã chuẩn hóa, còn được giữ lại để tính các cửa sổ trượt gần đây.

Nó cần thiết vì:

- bot detection không thể nhìn 1 log đơn lẻ
- anomaly detection cũng không thể nhìn 1 log đơn lẻ
- cả hai đều cần nhìn một khoảng thời gian gần đây

Ví dụ:

- nếu 5 log mới vừa đến từ Kafka
- nhưng cửa sổ bot là 60 giây
- thì stream phải giữ cả những log đến từ 10, 20, 30, 40, 50 giây trước

Tức là:

- Kafka batch chỉ cho biết “vừa mới đến thêm những gì”
- `recent_events` mới giữ được “bức tranh ngắn hạn đang diễn ra”

#### `traffic_buckets`

Đây là cấu trúc lưu số lượng request theo bucket thời gian để phục vụ forecasting.

Nó được index theo:

- `("system", "")`
- `("endpoint", endpoint_name)`

Mỗi key trỏ tới một map:

- `bucket_end -> request_count`

Ví dụ đơn giản:

- bucket 10:01 có 70 request toàn hệ thống
- bucket 10:02 có 74 request toàn hệ thống
- bucket 10:03 có 68 request toàn hệ thống

Thì forecasting mới có chuỗi lịch sử để dự đoán bucket tiếp theo.

Ý nghĩa:

- `recent_events` phục vụ bot và anomaly windows
- `traffic_buckets` phục vụ forecasting

### Checkpoint làm gì và tại sao cần

Stream processor có:

- `save_checkpoint`
- `load_checkpoint`

Checkpoint dùng để lưu lại `RuntimeState` ra file JSON.

Mục đích:

- nếu service restart
- hoặc bạn chạy demo nhiều lần
- thì có thể khôi phục phần state quan trọng thay vì mất sạch ngữ cảnh

Checkpoint đặc biệt có ích cho:

- forecasting, vì lịch sử bucket rất quan trọng
- sliding windows, vì nếu mất state thì prediction đầu tiên sau restart sẽ nghèo ngữ cảnh hơn

Khi thuyết trình có thể nói:

`Checkpoint giúp stream processor không hoàn toàn mất trí nhớ giữa các lần chạy, đặc biệt với những bài toán cần lịch sử ngắn hạn.`

### Raw log được xử lý đầu tiên như thế nào

Bước đầu tiên của stream owner không phải là gọi ML, mà là chuẩn hóa dữ liệu đầu vào.

Hàm `normalize_raw_log` làm việc này.

Nó đảm bảo mọi record sau khi đi vào pipeline đều có các trường chuẩn:

- `schema_version`
- `timestamp`
- `request_id`
- `session_id`
- `ip`
- `user_agent`
- `method`
- `endpoint`
- `route_template`
- `status`
- `latency_ms`

Ngoài ra nó còn tạo thêm:

- `event_time`

`event_time` là object `datetime` được parse từ `timestamp`, dùng để tính toán cửa sổ và bucket.

Ý nghĩa của bước normalize:

- dữ liệu từ generator hoặc replay có thể khác nhẹ về format
- stream processor cần một schema nội bộ ổn định để các bước sau không bị rối

### `window` là gì trong stream processor

Đây là phần rất quan trọng khi trình bày.

`Window` là một khoảng thời gian dùng để gom nhiều event lại thành một đơn vị phân tích.

Trong project này, window không phải là Kafka batch.

Kafka batch:

- là nhóm tin nhắn lấy được trong một lần poll
- phục vụ thu nhận dữ liệu
- không mang ý nghĩa ML

ML window:

- là khoảng thời gian phân tích
- phục vụ feature engineering
- có ý nghĩa nghiệp vụ

Ví dụ:

- một Kafka batch có thể chỉ có 5 log mới
- nhưng cửa sổ bot 60 giây có thể gồm 42 log của cùng một actor
- cửa sổ anomaly 60 giây có thể gồm 120 log của một endpoint

Đó là lý do stream processor phải giữ state thay vì chỉ xử lý từng batch độc lập.

### Bot window được xây như thế nào

Bot detection dùng cửa sổ:

- độ dài: `60 giây`
- slide: `10 giây`
- key nhóm: `ip + session_id + user_agent`

Các bước xử lý:

1. Stream lấy `recent_events`.
2. Tìm `latest event time`.
3. Căn `window_end` theo mốc slide.
4. Tạo `window_start = window_end - 60 giây`.
5. Chỉ lấy các event nằm trong khoảng `(window_start, window_end]`.
6. Nhóm các event theo:
   - `ip`
   - `session_id`
   - `user_agent`
7. Tính feature cho từng nhóm.

Feature bot gồm:

- `number_of_requests`
- `total_duration_s`
- `average_time_ms`
- `repeated_requests`
- `http_response_2xx`
- `http_response_3xx`
- `http_response_4xx`
- `http_response_5xx`
- `get_method`
- `post_method`
- `head_method`
- `other_method`
- `night`
- `max_barrage`

Ý nghĩa:

- phần này biến “nhiều request rời rạc” thành “hành vi của một actor trong 1 phút gần đây”

### Anomaly window được xây như thế nào

Anomaly detection dùng cửa sổ:

- độ dài: `60 giây`
- slide: `10 giây`
- key nhóm: `endpoint`
- baseline lookback: `300 giây`

Các bước xử lý:

1. Stream lấy `recent_events`.
2. Xác định `window_start` và `window_end` cho cửa sổ hiện tại.
3. Nhóm event theo `endpoint`.
4. Với mỗi endpoint, lấy:
   - event trong cửa sổ hiện tại
   - event trong baseline window phía trước
5. Tính feature hiện tại:
   - `request_count`
   - `avg_latency_ms`
   - `p95_latency_ms`
   - `p99_latency_ms`
   - `status_5xx_ratio`
6. Tính feature baseline:
   - `baseline_avg_latency_ms`
   - `baseline_5xx_ratio`

Ý nghĩa:

- bot detection hỏi: actor này có giống bot không?
- anomaly detection hỏi: endpoint này đang lệch bao xa so với bình thường gần đây?

### Forecast bucket được xây như thế nào

Forecast không dùng actor-level window như bot.

Nó dùng bucket thời gian:

- kích thước bucket: `60 giây`
- lịch sử: `10 bucket`

Các bước:

1. Mỗi raw log được gán vào một `bucket_end`.
2. Stream cập nhật `traffic_buckets`.
3. Stream giữ lịch sử cho:
   - toàn hệ thống
   - từng endpoint
4. Khi build forecast request, stream tạo chuỗi `history_rps`.
5. Từ chuỗi đó, stream tính:
   - `rolling_mean_5`
   - `rolling_std_5`
   - `hour_of_day`
   - `day_of_week`
6. Sau đó stream tạo request cho bucket tương lai:
   - `bucket_end`
   - `predicted_bucket_end`

Ý nghĩa:

- forecasting không nhìn từng request riêng lẻ
- nó nhìn lịch sử tải theo thời gian

### Workflow đầy đủ của `process_once()`

Đây là luồng xử lý quan trọng nhất mà Stream owner nên thuộc rất chắc.

Mỗi vòng xử lý, `process_once()` làm như sau:

1. Tạo hoặc nhận `RuntimeState`.
2. Gọi `fetch_kafka_batch(settings)` để đọc một batch từ Kafka.
3. Nếu Kafka không có dữ liệu:
   - load sample logs từ `contracts/examples/raw-logs.sample.jsonl`
   - gán `source = "sample"`
4. Chuẩn hóa dữ liệu bằng `normalize_raw_log`.
5. Cập nhật state bằng `update_runtime_state`.
6. Từ state hiện tại, build:
   - `bot_requests`
   - `anomaly_requests`
   - `forecast_requests`
7. Kiểm tra ML API có sẵn không bằng `ml_api_ready`.
8. Nếu ML API sẵn sàng:
   - gọi `/predict/bot`
   - gọi `/predict/forecast`
   - gọi `/predict/anomaly`
9. Nếu ML API lỗi:
   - fallback sang `predict_bot_mock`
   - `predict_forecast_mock`
   - `predict_anomaly_mock`
10. Dùng prediction để build 4 nhóm row:
   - `processed_logs`
   - `bot_feature_windows`
   - `load_forecasts`
   - `anomaly_alerts`
11. Thử ghi tất cả vào ClickHouse.
12. Nếu ClickHouse lỗi:
   - dump ra file fallback
13. Trả về summary:
   - source
   - sink
   - count
   - số bot windows
   - số forecasts
   - số anomalies

### `update_runtime_state()` xử lý cụ thể như thế nào

Đây là phần cốt lõi để hiểu stateful processing.

Hàm này làm 3 việc:

1. Thêm raw logs mới vào `recent_events`
2. Cắt tỉa `recent_events` để chỉ giữ khoảng thời gian cần thiết
3. Cập nhật `traffic_buckets` và cắt tỉa lịch sử cũ

Chi tiết:

- stream không giữ vô hạn tất cả log đã từng thấy
- nó chỉ giữ đủ lâu để:
  - tính bot windows
  - tính anomaly windows
  - tính baseline cho anomaly

Sau đó:

- mỗi event mới lại được map vào bucket forecast
- cả bucket hệ thống lẫn bucket từng endpoint đều được tăng count
- các bucket quá cũ sẽ bị xóa đi để state không phình mãi

Ý nghĩa:

- state luôn “đủ dùng”
- nhưng không bị phình vô hạn

### Spark và Python xử lý khác nhau ra sao

Stream owner đã xây hai cách build window:

- Spark-backed builders
- Python builders

Hiện tại code hoạt động theo chiến lược:

1. thử Spark trước
2. nếu Spark lỗi hoặc không sẵn sàng thì fallback sang Python

Điều này có lợi vì:

- khi có môi trường phù hợp thì Spark thể hiện hướng xử lý dữ liệu lớn
- khi demo local đơn giản thì Python path vẫn chạy được

Nói cách khác:

- team không bị khóa cứng vào Spark
- nhưng vẫn thể hiện được hướng kiến trúc big data

### Từ prediction đến dữ liệu analytics

Sau khi có prediction, stream processor không dừng ở việc in ra màn hình.

Nó biến prediction thành 4 loại dữ liệu cụ thể:

1. `processed_logs`
   - mỗi raw log được enrich thêm:
     - `bot_score`
     - `is_bot`
     - `predicted_load`
     - `anomaly_score`
     - `is_anomaly`
2. `bot_feature_windows`
   - lưu feature bot và kết quả bot prediction
3. `load_forecasts`
   - lưu kết quả dự báo theo bucket
4. `anomaly_alerts`
   - lưu feature anomaly và kết quả anomaly prediction

Đây chính là bước chuyển từ “pipeline kỹ thuật” sang “dữ liệu phân tích dùng được”.

### Fallback chain của Stream owner

Stream owner không chỉ xử lý happy path.

Role này còn phải nghĩ đến các tình huống lỗi:

1. Kafka không có dữ liệu
   - dùng sample logs
2. ML API không sẵn sàng
   - dùng local mock analyzers
3. ClickHouse không ghi được
   - dump kết quả vào file

Ý nghĩa của fallback chain:

- hệ thống demo không bị chết vì thiếu một dependency
- team vẫn chứng minh được pipeline end-to-end
- có thể test riêng từng phần mà không cần toàn bộ stack luôn hoàn hảo

### Cách giải thích phần này khi đứng thuyết trình

Một đoạn nói ngắn nhưng chuẩn:

`Phần Stream không chỉ là đọc dữ liệu từ Kafka rồi chuyển tiếp sang ML. Đây là nơi giữ state, cắt cửa sổ thời gian, tính feature, gọi model, ghép prediction vào dữ liệu và chịu trách nhiệm fallback khi dependency gặp lỗi.`

### Câu trả lời nếu bị hỏi sâu

Nếu bị hỏi `vì sao stream là phần quan trọng nhất`, có thể trả lời:

`Vì ML không làm feature engineering từ raw log, còn analytics cũng không xử lý ngữ nghĩa thời gian. Chỉ stream processor mới hiểu raw event phải được gom thành actor behavior window, endpoint anomaly window hay traffic history bucket như thế nào.`

Nếu bị hỏi `window khác batch ở đâu`, có thể trả lời:

`Batch là đơn vị lấy dữ liệu từ Kafka, còn window là đơn vị phân tích. Một batch chỉ cho biết log mới đến, còn window mới cho biết hành vi xảy ra trong một khoảng thời gian có ý nghĩa.`

Nếu bị hỏi `RuntimeState quan trọng ở đâu`, có thể trả lời:

`Nếu không có RuntimeState thì mỗi lần poll chỉ nhìn thấy vài log mới, không đủ ngữ cảnh để tính bot behavior, anomaly baseline hay lịch sử forecast.`

### Artifact tiêu biểu để chứng minh

- `stream-processor/src/stream_processor/main.py`
- `stream-processor/src/stream_processor/mock_analyzer.py`
- `stream-processor/output/stream-checkpoint.json`
- `stream-processor/requirements.txt`
- `stream-processor/requirements-spark.txt`
- `stream-processor/Dockerfile`
- `tests/test_stream_processor.py`

### Giá trị phần việc này mang lại

- Đây là nơi biến raw data thành dữ liệu có nghĩa cho ML.
- Đây cũng là lớp đảm bảo hệ thống không chết ngay khi ML API hoặc ClickHouse có vấn đề.
- Đây là thành phần “gắn” tất cả module còn lại vào nhau.

### Khi đứng thuyết trình nên nói gì

`Phần em là lõi xử lý của pipeline. Em chịu trách nhiệm nhận raw logs, tạo feature windows cho ba bài toán, gọi ML API, rồi ghi kết quả sang tầng phân tích.`

### Những điểm kỹ thuật nên nhấn mạnh

- phân biệt Kafka batch và ML window
- stateful processing
- pure Python vs PySpark
- fallback chain
- checkpoint để giữ trạng thái

---

## 8.4 Thành viên 3: ML Owner

### Ownership

- `ml-api/`

### Những gì role này đã làm

1. Xây `FastAPI` service trong `ml-api/src/ml_api/main.py`.
2. Định nghĩa request/response model bằng `Pydantic` cho ba endpoint:
   - `/predict/bot`
   - `/predict/forecast`
   - `/predict/anomaly`
3. Tạo endpoint `/healthz` để kiểm tra trạng thái service và mode.
4. Xây lõi suy luận trong `ml-api/src/ml_api/analyzer.py`.
5. Hỗ trợ hai chế độ vận hành:
   - `mock mode`
   - `model mode`
6. Viết heuristic logic khi chưa có model artifact.
7. Load model thật từ `.joblib` khi artifact tồn tại.
8. Xây feature mapping cho bot model.
9. Tạo `forecast guardrail` để chặn dự báo vọt bất thường.
10. Cấu hình threshold và model behavior bằng file JSON config.
11. Tích hợp model artifacts thật:
   - `bot_model.joblib`
   - `forecast_model.joblib`
   - `anomaly_model.joblib`
12. Chuẩn bị dữ liệu và tài liệu handoff cho phần ML:
   - `ML_HANDOFF_REPORT.md`
   - `ml-api/data/*.csv`
   - `ml-api/models/colab.md`
13. Viết test cho:
   - mode switching
   - model artifact loading
   - prediction determinism
   - FastAPI endpoints

### Artifact tiêu biểu để chứng minh

- `ml-api/src/ml_api/main.py`
- `ml-api/src/ml_api/analyzer.py`
- `ml-api/models/bot_model.joblib`
- `ml-api/models/forecast_model.joblib`
- `ml-api/models/anomaly_model.joblib`
- `ml-api/models/model_config.json`
- `ml-api/models/forecast_model_config.json`
- `ml-api/models/anomaly_model_config.json`
- `ml-api/data/simple_features.csv`
- `ml-api/data/forecast_training_dataset.csv`
- `ml-api/data/anomaly_training_dataset.csv`
- `ML_HANDOFF_REPORT.md`
- `tests/test_ml_api.py`

### Giá trị phần việc này mang lại

- Tách logic ML ra khỏi stream processor.
- Cho phép service hóa khả năng suy luận.
- Hỗ trợ vừa demo bằng mock, vừa chạy với model thật khi artifact đã sẵn sàng.

### Khi đứng thuyết trình nên nói gì

`Phần em phụ trách là biến feature payload thành prediction. Em xây ML API theo hướng service hóa, có kiểm soát contract chặt và có cả mock mode lẫn model mode để hệ thống không bị phụ thuộc tuyệt đối vào artifact.`

### Những điểm kỹ thuật nên kể ra

- FastAPI + Pydantic validation
- dual-mode inference
- datasets thực tế
- guardrail cho forecast
- config-driven model loading

### Chi tiết dataset nên nói khi thuyết trình

Bot:

- nguồn: web robot detection dataset
- model: `RandomForestClassifier`
- đầu ra: `ROBOT`

Forecast:

- nguồn: Wikimedia Analytics API
- model: `RandomForestRegressor`
- đầu ra: `target_next_rps`

Anomaly:

- nguồn: Microsoft Cloud Monitoring Dataset
- model: `RandomForestClassifier`
- đầu ra: `target_is_anomaly`

---

## 8.5 Thành viên 4: Analytics Owner

### Ownership

- `analytics/`

### Những gì role này đã làm

1. Thiết kế tầng lưu trữ phân tích trên ClickHouse.
2. Viết DDL cho các bảng chính trong `analytics/sql/create_processed_logs.sql`.
3. Tạo materialized views trong `analytics/sql/create_materialized_views.sql`.
4. Chuẩn bị seed data trong `analytics/sql/seed_processed_logs.sql`.
5. Viết script `ensure_seed.py` để:
   - tạo bảng nếu chưa có
   - tạo materialized views
   - seed dữ liệu nếu bảng trống
6. Viết `query_smoke.py` để kiểm tra nhanh các bảng analytics.
7. Cấu hình provisioning datasource cho Grafana.
8. Cấu hình provisioning dashboard cho Grafana.
9. Thiết kế dashboard `aiops-overview.json` để hiển thị:
   - requests per minute
   - next minute forecast
   - top bot entities
   - endpoint anomaly alerts
10. Phối hợp với stream owner để đảm bảo schema row ghi xuống ClickHouse phù hợp dashboard.
11. Viết test asset cho analytics để kiểm tra DDL, seed và dashboard.

### Artifact tiêu biểu để chứng minh

- `analytics/sql/create_processed_logs.sql`
- `analytics/sql/create_materialized_views.sql`
- `analytics/sql/seed_processed_logs.sql`
- `analytics/scripts/ensure_seed.py`
- `analytics/scripts/query_smoke.py`
- `analytics/grafana/dashboards/aiops-overview.json`
- `analytics/grafana/provisioning/datasources/datasource.yml`
- `analytics/grafana/provisioning/dashboards/dashboard.yml`
- `tests/test_analytics_assets.py`

### Giá trị phần việc này mang lại

- Biến pipeline từ “chạy được” thành “quan sát được”.
- Tạo lớp phân tích mà người dùng hoặc giảng viên có thể nhìn thấy ngay.
- Giúp kết quả ML trở thành dashboard vận hành thay vì chỉ là JSON.

### Khi đứng thuyết trình nên nói gì

`Phần em phụ trách là tầng phân tích và trực quan hóa. Em chuẩn bị schema ClickHouse, seed data, smoke query và dashboard Grafana để kết quả từ stream processor có thể được nhìn thấy và kiểm tra ngay.`

### Những điểm kỹ thuật nên nhấn mạnh

- ClickHouse tables và order keys
- materialized views
- Grafana auto-provisioning
- smoke query để verify dữ liệu

---

## 9. Slide nội dung chi tiết cho từng người

## 9.1 Tech Lead nói slide nào và nói gì

### Slide 1: Giới thiệu đề tài

Nội dung nên nói:

`Nhóm em xây dựng một pipeline AIOps local-first để phân tích log truy cập theo thời gian thực. Hệ thống tập trung vào ba bài toán là phát hiện bot, dự báo tải và phát hiện bất thường.`

### Slide 2: Tại sao cần hệ thống này

Nội dung nên nói:

`Trong vận hành hệ thống web, log truy cập chứa rất nhiều tín hiệu quan trọng. Nếu chỉ lưu log mà không xử lý thành insight thì rất khó phát hiện bot, dự báo tải hoặc nhận biết sự cố sớm.`

### Slide 3: Kiến trúc tổng thể

Nội dung nên nói:

`Pipeline của nhóm đi từ generator sang Kafka, sau đó stream processor tạo feature windows, gửi sang ML API, lưu xuống ClickHouse và hiển thị trên Grafana.`

### Slide 4: Contracts và teamwork

Nội dung nên nói:

`Điểm cốt lõi của team là chia ownership rất rõ. Mỗi module có contract riêng nên các thành viên có thể phát triển song song mà vẫn tích hợp được.`

## 9.2 Thành viên 1 nói slide nào và nói gì

### Slide 5: Synthetic generator

Nội dung nên nói:

`Em xây generator theo dạng synthetic traffic có nhiều phase để mô phỏng các tình huống thực tế như bot scraping, login probing, user browsing và incident 5xx.`

### Slide 6: Replay access logs

Nội dung nên nói:

`Ngoài synthetic data, nhóm còn có replay tool để đọc access log thật, suy ra session, route template và phát lại theo time scale nhanh hơn realtime.`

## 9.3 Thành viên 2 nói slide nào và nói gì

### Slide 7: Windowing và state

Nội dung nên nói:

`Phần stream là lõi của hệ thống. Em nhận raw logs từ Kafka, chuẩn hóa dữ liệu, giữ runtime state và tạo feature windows riêng cho từng bài toán ML.`

### Slide 8: Fallback và ghi dữ liệu

Nội dung nên nói:

`Em thiết kế thêm fallback chain để hệ thống chịu lỗi tốt hơn. Nếu ML API không sẵn sàng thì dùng mock analyzer, nếu ClickHouse lỗi thì ghi ra file fallback.`

## 9.4 Thành viên 3 nói slide nào và nói gì

### Slide 9: ML API

Nội dung nên nói:

`ML API được tách thành service riêng với FastAPI. Mỗi endpoint nhận đúng một loại feature payload thay vì một raw event chung chung.`

### Slide 10: Model mode và mock mode

Nội dung nên nói:

`Phần ML có hai chế độ. Khi có model artifact thật thì hệ thống suy luận bằng scikit-learn; khi chưa có artifact thì dùng mock logic tất định để pipeline vẫn hoạt động.`

## 9.5 Thành viên 4 nói slide nào và nói gì

### Slide 11: ClickHouse

Nội dung nên nói:

`Em xây các bảng ClickHouse để lưu processed logs và các đầu ra phân tích. Tầng này giúp các kết quả từ stream có thể được truy vấn nhanh và trực tiếp.`

### Slide 12: Grafana dashboard

Nội dung nên nói:

`Em cấu hình dashboard để hiển thị traffic, forecast, bot entities và anomaly alerts, giúp biến dữ liệu kỹ thuật thành góc nhìn vận hành dễ hiểu.`

---

## 10. Demo plan đề xuất

## 10.1 Mục tiêu demo

Demo cần chứng minh được 4 ý:

1. Generator tạo dữ liệu.
2. Stream processor đọc và xử lý được.
3. ML API trả prediction.
4. ClickHouse hoặc Grafana nhận được kết quả cuối.

## 10.2 Demo tối thiểu

Kịch bản demo tối thiểu:

1. Khởi động infra.
2. Chạy ML API.
3. Chạy stream processor.
4. Chạy generator.
5. Mở Grafana hoặc chạy smoke query.

## 10.3 Phân vai trong demo

| Người | Việc làm khi demo |
|---|---|
| Tech Lead | Giới thiệu flow demo và chuyển lượt |
| Thành viên 1 | Chạy generator hoặc replay |
| Thành viên 2 | Cho thấy stream đang build windows và ghi output |
| Thành viên 3 | Mở `/healthz` hoặc giải thích response prediction |
| Thành viên 4 | Mở ClickHouse query hoặc Grafana dashboard |

## 10.4 Demo script ngắn

Tech Lead:

`Bây giờ nhóm sẽ chạy demo theo đúng thứ tự của pipeline để thấy dữ liệu đi từ raw log đến dashboard.`

Thành viên 1:

`Em chạy generator để tạo traffic giả lập theo nhiều phase khác nhau.`

Thành viên 2:

`Stream processor đang nhận batch từ Kafka, tạo feature windows và gửi payload sang ML API.`

Thành viên 3:

`ML API nhận payload theo từng task và trả về prediction tương ứng.`

Thành viên 4:

`Kết quả cuối cùng đã được ghi vào ClickHouse và hiển thị trên dashboard.`

---

## 11. Điểm mạnh mà team nên nhấn mạnh

1. Kiến trúc v2 tách raw data và ML features rất đúng hướng.
2. Có ownership rõ ràng theo module.
3. Có contracts, examples và validator để giảm lỗi tích hợp.
4. Có cả dữ liệu synthetic lẫn replay log thật.
5. Có cả mock mode và model mode.
6. Có fallback chain nên hệ thống chịu lỗi tốt hơn mức demo thông thường.
7. Có ClickHouse và Grafana nên kết quả nhìn thấy được, không chỉ nằm trong log.
8. Có test cho generator, stream, ml-api, contracts và analytics assets.
9. Có local-first workflow cho việc phát triển và demo.

---

## 12. Điểm yếu hoặc rủi ro nên nói trước nếu bị hỏi

1. Một số tài liệu còn chưa đồng bộ hoàn toàn với implementation hiện tại.
   Gợi ý trả lời: `Nhóm đã nhận ra và đang chuẩn hóa lại narrative theo Kafka-based implementation hiện tại.`

2. Chưa có end-to-end integration test đầy đủ với toàn bộ stack thật.
   Gợi ý trả lời: `Hiện nhóm đã có unit tests tốt và smoke tests, bước tiếp theo là bổ sung e2e test.`

3. Chưa có training pipeline tái lập hoàn toàn trong repo.
   Gợi ý trả lời: `Hiện việc training chạy trên Colab, còn repo tập trung vào serving và integration.`

4. Logging và observability ứng dụng còn cơ bản.
   Gợi ý trả lời: `Đây là phần roadmap tiếp theo, ví dụ structured logging và metrics endpoint.`

5. Bảo mật local dev đang nới lỏng.
   Gợi ý trả lời: `Cấu hình này phù hợp môi trường local demo, chưa phải cấu hình production.`

---

## 13. Câu hỏi phản biện có thể gặp

### Câu hỏi 1

`Tại sao không gửi raw log trực tiếp sang ML?`

Trả lời gợi ý:

`Vì raw log mới chỉ là dữ liệu event-level. Ba bài toán ML trong dự án đều cần feature ở mức cửa sổ hoặc lịch sử, nên stream processor phải đóng vai trò feature engineering trước khi gọi ML.`

### Câu hỏi 2

`Tại sao lại tách ML API thành service riêng?`

Trả lời gợi ý:

`Tách service giúp stream processor tập trung vào xử lý dữ liệu và windowing, còn ML API tập trung vào suy luận. Cách này cũng thuận lợi hơn nếu sau này thay model hoặc scale riêng tầng ML.`

### Câu hỏi 3

`Nếu ML API chết thì hệ thống có dừng không?`

Trả lời gợi ý:

`Không dừng ngay. Stream processor có fallback sang mock analyzer để pipeline vẫn chạy được trong bối cảnh demo hoặc khi dependency chưa sẵn sàng.`

### Câu hỏi 4

`Dự án có dùng dữ liệu thật không?`

Trả lời gợi ý:

`Có. Ngoài synthetic generator, nhóm có replay access log thật và phần ML cũng dùng dataset thực tế cho forecast và anomaly.`

### Câu hỏi 5

`Vì sao chọn ClickHouse?`

Trả lời gợi ý:

`Vì đây là OLAP database tối ưu cho truy vấn phân tích theo thời gian, rất phù hợp để lưu processed logs, forecasts và anomaly alerts phục vụ dashboard.`

### Câu hỏi 6

`Nếu dữ liệu tăng lớn hơn nhiều thì sao?`

Trả lời gợi ý:

`Thiết kế hiện tại đã có hướng mở rộng: broker tách rời bằng Kafka, stream có đường PySpark, ML là service riêng, analytics là ClickHouse. Tuy nhiên cần bổ sung backpressure, scale strategy và e2e test cho production-grade.`

---

## 14. Checklist trước ngày thuyết trình

1. Thống nhất cách nói:
   dùng `Kafka`, không dùng `NATS` khi mô tả implementation hiện tại.
2. Kiểm tra models có đủ trong `ml-api/models/`.
3. Kiểm tra dashboard Grafana đã được provision.
4. Kiểm tra ClickHouse có dữ liệu seed hoặc dữ liệu demo.
5. Kiểm tra `make` hoặc script local chạy được trên máy demo.
6. Chạy thử demo ít nhất 1 lần đầy đủ.
7. Mỗi người tập nói đúng phần mình trong `3-6 phút`.
8. Tech Lead chuẩn bị 1 slide backup về kiến trúc nếu hội đồng hỏi sâu.
9. Chuẩn bị sẵn câu trả lời cho phần:
   - contracts
   - fallback
   - model thật hay mock
   - dữ liệu thật hay synthetic

---

## 15. Gợi ý bố cục slide thực tế

Một deck `12-14 slide` là đẹp nhất:

1. Title + team members
2. Problem statement
3. Project goals
4. Architecture overview
5. Contracts and v2 design principle
6. Generator
7. Stream processor
8. ML API
9. Analytics
10. Demo flow
11. Team collaboration and testing
12. Strengths and limitations
13. Roadmap
14. Q&A

---

## 16. Roadmap nếu muốn chốt bài đẹp hơn

Nếu muốn kết thúc chuyên nghiệp, Tech Lead có thể chốt bằng 4 hướng mở rộng:

1. Thêm end-to-end integration testing.
2. Thêm structured logging và metrics.
3. Đưa training pipeline vào repo thay vì chỉ ở Colab.
4. Tăng production readiness cho security, deployment và scalability.

---

## 17. Kết luận ngắn gọn để cả team thống nhất

Một câu kết luận đẹp để Tech Lead nói:

`Điểm quan trọng nhất của dự án không chỉ là có một model dự đoán, mà là xây được một pipeline có contracts rõ ràng, có feature engineering đúng ngữ nghĩa, có khả năng fallback và có đầu ra phân tích quan sát được. Đó là lý do nhóm chọn cách chia thành 5 role rõ ràng và ghép lại thành một hệ thống hoàn chỉnh.`
