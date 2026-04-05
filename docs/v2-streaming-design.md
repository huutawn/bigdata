# Giải thích Thiết kế Luồng dữ liệu V2 (V2 Streaming Design Explained)

Tài liệu này giải thích ý nghĩa của `v2` trong dự án này, cách dữ liệu di chuyển từ log thô đến các dự đoán ML, cách các gói dữ liệu đặc trưng (feature payloads) được xây dựng, và sự khác biệt giữa `Kafka batching` (gom nhóm Kafka) và `ML windowing` (cửa sổ ML).

## 1. Ý nghĩa của `v2`

`v2` là kiến trúc thứ hai của dự án.

Ý tưởng cũ gần như là:

`một sự kiện thô -> một lệnh gọi ML chung -> một dự đoán`

Thiết kế đó quá yếu đối với việc phân tích hành vi thực tế vì hầu hết các tín hiệu hữu ích không xuất hiện trong một bản ghi log duy nhất. Các đặc trưng như tỷ lệ yêu cầu, các route lặp lại, tỷ lệ lỗi, tính bùng nổ và độ trễ trượt chỉ xuất hiện khi chúng ta nhìn vào nhiều sự kiện cùng nhau theo thời gian.

Vì vậy, `v2` thay đổi dự án thành:

`sự kiện thô -> trạng thái luồng -> cửa sổ đặc trưng (Spark) -> gói dữ liệu ML cụ thể theo nhiệm vụ -> dự đoán`

Đây là thay đổi thiết kế then chốt.

## 2. Tại sao cần `v2`

Một log gateway thô duy nhất chỉ cho chúng ta biết về một yêu cầu tại một thời điểm.
Điều đó đủ để lưu trữ sự kiện, nhưng không đủ để trả lời các câu hỏi như:

- IP này có đang hành xử giống bot không?
- Lưu lượng truy cập có khả năng tăng trong phút tiếp theo không?
- Endpoint này hiện có bất thường so với đường cơ sở (baseline) gần đây của nó không?

Những câu hỏi đó yêu cầu ngữ cảnh trên nhiều sự kiện.

Đó là lý do tại sao `v2` giới thiệu:

- log thô phong phú hơn
- trạng thái trong bộ xử lý luồng (stream processor)
- các cửa sổ thời gian
- các gói dữ liệu riêng biệt để phát hiện bot, dự báo và phát hiện bất thường

## 3. Quy trình từ đầu đến cuối (End-to-end flow)

Quy trình `v2` đầy đủ là:

`generator -> Kafka -> stream-processor (Spark) -> ml-api -> ClickHouse -> Grafana`

Chi tiết hơn:

1. `generator` đẩy các sự kiện yêu cầu thô lên Kafka topic `logs.raw`
2. `stream-processor` đọc một nhóm từ Kafka consumer
3. luồng dữ liệu chuẩn hóa các sự kiện đó và thêm chúng vào trạng thái trong bộ mới (in-memory state)
4. luồng dùng **Spark** để gom nhóm trạng thái vào các cửa sổ phân tích (analysis windows) và các nhóm dự báo (forecast buckets)
5. luồng xây dựng các gói dữ liệu ML cho từng nhiệm vụ
6. `ml-api` trả về các dự đoán cụ thể cho từng nhiệm vụ
7. luồng ghi các hàng đã được làm giàu và các bảng dự đoán vào ClickHouse
8. Grafana đọc các bảng ClickHouse để hiển thị trên bảng điều khiển (dashboards)

## 4. Hợp đồng log thô trong `v2` (Raw log contract in `v2`)

Một log thô là đầu vào cấp độ sự kiện. Nó không nên chứa sẵn các đầu ra ML như `is_bot` hay `predicted_load`.

Một log thô `v2` điển hình trông như thế này:

```json
{
  "schema_version": "v2",
  "timestamp": "2026-03-24T10:00:00Z",
  "request_id": "req-000001",
  "session_id": "sess-001",
  "ip": "1.2.3.4",
  "user_agent": "Mozilla/5.0",
  "method": "GET",
  "endpoint": "/api/v1/products",
  "route_template": "/api/v1/products",
  "status": 200,
  "latency_ms": 150
}
```

Tại sao các trường này quan trọng:

- `timestamp`: thời gian sự kiện để gom nhóm, sắp xếp và tạo cửa sổ
- `request_id`: định danh sự kiện ổn định
- `session_id`: gom nhóm các yêu cầu liên quan từ cùng một phiên (session)
- `ip`: khóa thực thể quan trọng để phân tích hành vi
- `user_agent`: tín hiệu mạnh để nhận diện bot và là thuộc tính gom nhóm hữu ích
- `method`: cần thiết cho tỷ lệ các phương thức HTTP
- `endpoint` và `route_template`: cần thiết để phân tích các route lặp lại và giám sát cấp độ endpoint
- `status`: cần thiết cho tỷ lệ lỗi 2xx, 4xx và 5xx
- `latency_ms`: cần thiết cho các đặc trưng về bất thường và hiệu suất

## 5. Phân biệt quan trọng nhất: Nhóm Kafka (Kafka batch) so với Cửa sổ ML (ML window)

Hai ý tưởng này hoàn toàn khác nhau.

### Nhóm Kafka (Kafka batch)

Một `Kafka batch` chỉ là một nhóm vận chuyển nhỏ.
Nó trả lời câu hỏi:

"Chúng ta lấy bao nhiêu tin nhắn từ Kafka trong một chu kỳ poll?"

Trong dự án này, điều đó được kiểm soát bởi:

- `STREAM_BATCH_SIZE`
- `STREAM_POLL_TIMEOUT_SECONDS`

Hành vi hiện tại trong bộ xử lý luồng:

- subscribe vào topic `logs.raw`
- thu thập các messages cho đến khi:
  - nhóm đạt tới `STREAM_BATCH_SIZE`, hoặc
  - hết thời gian poll (timeout)
- sau đó dừng đọc và xử lý bất cứ thứ gì đã thu thập được

Vì vậy, một nhóm Kafka là về hiệu quả thu nạp dữ liệu, không phải về ngữ nghĩa ML.

### Cửa sổ ML (ML window)

Một `ML window` là một cửa sổ phân tích.
Nó trả lời câu hỏi:

"Những sự kiện nào nên được gom nhóm lại với nhau để tính toán các đặc trưng hành vi?"

Ví dụ:

- cửa sổ phát hiện bot: 60 giây cuối cùng cho một cặp `ip + session_id + user_agent`
- cửa sổ bất thường: 60 giây cuối cùng cho một `endpoint`
- nhóm dự báo (forecast bucket): số lượng yêu cầu theo từng phút trong lịch sử gần đây

Vì vậy:

- `Kafka batch` = nhóm vận chuyển vi mô (transport micro-batch)
- `ML window` = gom nhóm phân tích theo thời gian

Sự phân biệt này là cực kỳ quan trọng.

## 6. Điều gì xảy ra bên trong bộ xử lý luồng

Bộ xử lý luồng thực hiện bốn công việc chính.

### Bước A. Chuẩn hóa các sự kiện thô

Mỗi sự kiện đến đều được chuẩn hóa thành một cấu trúc nội bộ nhất quán.

Giai đoạn này:

- ánh xạ các trường vào hình dạng `v2`
- chuyển đổi dấu thời gian thành `event_time`
- viết hoa các phương thức HTTP
- điền các giá trị mặc định để tương thích ngược khi cần thiết

Điều này quan trọng vì logic cửa sổ hạ nguồn phải hoạt động trên một sơ đồ ổn định.

### Bước B. Cập nhật trạng thái luồng (stream state)

Bộ xử lý giữ trạng thái trong bộ nhớ.

Hai cấu trúc trạng thái quan trọng được sử dụng:

- `recent_events`: các sự kiện chuẩn hóa gần đây được giữ lại cho các cửa sổ trượt (sliding windows)
- `traffic_buckets`: số lượng yêu cầu trên mỗi phạm vi được sử dụng cho lịch sử dự báo

Tại sao cần trạng thái:

- chỉ riêng nhóm NATS mới nhất không chứa đủ ngữ cảnh
- các cửa sổ cần lịch sử gần đây, không chỉ vài sự kiện mới nhất
- dự báo cần các nhóm dữ liệu lịch sử, không chỉ các yêu cầu hiện tại

### Bước C. Xây dựng các cửa sổ phân tích và các nhóm dự báo

Từ trạng thái đó, bộ xử lý tạo ra các nhóm đặc trưng cụ thể cho từng nhiệm vụ.

### Bước D. Gọi các endpoint ML cụ thể cho từng nhiệm vụ

Luồng dữ liệu gửi đi ba loại gói dữ liệu khác nhau:

- gói dữ liệu bot tới `POST /predict/bot`
- gói dữ liệu dự báo tới `POST /predict/forecast`
- gói dữ liệu bất thường tới `POST /predict/anomaly`

Đây là một quyết định then chốt khác của `v2`: một nhiệm vụ, một hình dạng gói dữ liệu.

## 7. Cách xây dựng các gói dữ liệu bot (bot payloads)

Phát hiện bot dựa trên cửa sổ và dựa trên thực thể (entity-based).

### Khóa gom nhóm (Grouping key)

Các cửa sổ bot được gom nhóm theo:

`ip + session_id + user_agent`

Khóa này được sử dụng vì hành vi của bot thường gắn liền với một tác nhân (actor), không chỉ với một endpoint.

### Cấu hình cửa sổ

Thiết kế hiện tại:

- độ dài cửa sổ: `BOT_WINDOW_SECONDS` = 60
- trượt (slide): `BOT_WINDOW_SLIDE_SECONDS` = 10

Điều này có nghĩa là hệ thống đánh giá một cửa sổ hành vi trượt một phút sau mỗi mười giây.

### Các đặc trưng được tạo ra từ log thô

Bộ xử lý tính toán các đặc trưng như:

- `number_of_requests`: số lượng yêu cầu
- `total_duration_s`: tổng thời gian (giây)
- `average_time_ms`: thời gian trung bình (mili giây)
- `repeated_requests`: tỷ lệ yêu cầu lặp lại
- `http_response_2xx`: tỷ lệ phản hồi 2xx
- `http_response_3xx`: tỷ lệ phản hồi 3xx
- `http_response_4xx`: tỷ lệ phản hồi 4xx
- `http_response_5xx`: tỷ lệ phản hồi 5xx
- `get_method`: tỷ lệ phương thức GET
- `post_method`: tỷ lệ phương thức POST
- `head_method`: tỷ lệ phương thức HEAD
- `other_method`: tỷ lệ phương thức khác
- `night`: thời điểm ban đêm
- `max_barrage`: đợt bùng nổ tối đa

Những đặc trưng này không được lưu trữ trực tiếp trong log thô.
Chúng được tạo ra từ nhiều sự kiện thô bên trong cửa sổ hiện tại.

### Gói dữ liệu yêu cầu Bot (Bot request payload)

```json
{
  "feature_version": "v2",
  "window_start": "2026-03-24T10:00:00Z",
  "window_end": "2026-03-24T10:01:00Z",
  "entity": {
    "ip": "1.2.3.4",
    "session_id": "sess-001",
    "user_agent": "Mozilla/5.0"
  },
  "features": {
    "number_of_requests": 42,
    "total_duration_s": 58,
    "average_time_ms": 120,
    "repeated_requests": 0.83,
    "http_response_2xx": 0.76,
    "http_response_3xx": 0.02,
    "http_response_4xx": 0.18,
    "http_response_5xx": 0.04,
    "get_method": 0.91,
    "post_method": 0.07,
    "head_method": 0.01,
    "other_method": 0.01,
    "night": 0,
    "max_barrage": 12
  }
}
```

## 8. Cách xây dựng các gói dữ liệu bất thường (anomaly payloads)

Phát hiện bất thường dựa trên endpoint và so sánh cửa sổ hiện tại với đường cơ sở (baseline) gần đây.

### Khóa gom nhóm (Grouping key)

Các cửa sổ bất thường được gom nhóm theo:

`endpoint`

### Cấu hình cửa sổ

Thiết kế hiện tại:

- độ dài cửa sổ: `ANOMALY_WINDOW_SECONDS` = 60
- trượt (slide): `ANOMALY_WINDOW_SLIDE_SECONDS` = 10
- xem lại đường cơ sở: `ANOMALY_BASELINE_LOOKBACK_SECONDS` = 300

Điều đó có nghĩa là:

- tính toán một cửa sổ endpoint hoạt động trong một phút
- so sánh nó với hành vi của endpoint trong khoảng năm phút trước đó

### Các đặc trưng được tạo ra từ log thô

Bộ xử lý tính toán:

- `request_count`: số lượng yêu cầu
- `avg_latency_ms`: độ trễ trung bình
- `p95_latency_ms`: độ trễ ở mức p95
- `p99_latency_ms`: độ trễ ở mức p99
- `status_5xx_ratio`: tỷ lệ lỗi 5xx
- `baseline_avg_latency_ms`: độ trễ trung bình đường cơ sở
- `baseline_5xx_ratio`: tỷ lệ 5xx đường cơ sở

Những đặc trưng này giúp lớp ML biết liệu độ trễ hiện tại và hành vi lỗi có bị sai lệch so với hành vi bình thường gần đây hay không.

### Gói dữ liệu yêu cầu bất thường (Anomaly request payload)

```json
{
  "feature_version": "v2",
  "window_start": "2026-03-24T10:00:00Z",
  "window_end": "2026-03-24T10:01:00Z",
  "entity": {
    "endpoint": "/api/v1/orders"
  },
  "features": {
    "request_count": 120,
    "avg_latency_ms": 420,
    "p95_latency_ms": 1800,
    "p99_latency_ms": 3200,
    "status_5xx_ratio": 0.12,
    "baseline_avg_latency_ms": 180,
    "baseline_5xx_ratio": 0.01
  }
}
```

## 9. Cách xây dựng các gói dữ liệu dự báo (forecast payloads)

Dự báo không dựa trên một tác nhân duy nhất. Nó dựa trên lịch sử lưu lượng truy cập theo thời gian.

### Khóa gom nhóm (Grouping keys)

Các nhóm dự báo được duy trì cho:

- `system`: toàn hệ thống
- `endpoint`: từng endpoint

### Cấu hình nhóm dữ liệu (Bucket configuration)

Thiết kế hiện tại:

- kích thước nhóm: `FORECAST_BUCKET_SECONDS` = 60
- kích thước lịch sử: `FORECAST_HISTORY_SIZE` = 10

Điều này có nghĩa là luồng dữ liệu giữ một lịch sử trượt của các lượt đếm theo từng phút.

### Cách tính toán lượt đếm (How counts are built)

Với mỗi sự kiện đã chuẩn hóa:

- căn chỉnh thời gian sự kiện theo thời điểm kết thúc nhóm của nó
- tăng bộ đếm yêu cầu cho phạm vi liên quan
- chỉ giữ lại các nhóm dữ liệu gần đây cần thiết cho lịch sử

### Các đặc trưng được tạo ra từ lịch sử

Luồng dữ liệu xây dựng gói dữ liệu dự báo từ các lượt đếm gần đây như:

- `history_rps`: lịch sử RPS
- `rolling_mean_5`: giá trị trung bình trượt trong 5 chu kỳ
- `rolling_std_5`: độ lệch chuẩn trượt trong 5 chu kỳ
- `hour_of_day`: giờ trong ngày
- `day_of_week`: ngày trong tuần

### Gói dữ liệu yêu cầu dự báo (Forecast request payload)

```json
{
  "feature_version": "v2",
  "bucket_end": "2026-03-24T10:01:00Z",
  "predicted_bucket_end": "2026-03-24T10:02:00Z",
  "target": {
    "scope": "system",
    "endpoint": ""
  },
  "history_rps": [55, 58, 61, 64, 62, 70],
  "features": {
    "rolling_mean_5": 63.0,
    "rolling_std_5": 4.2,
    "hour_of_day": 10,
    "day_of_week": 1
  }
}
```

Ở đây:

- `bucket_end` là mốc kết thúc của bucket quan sát gần nhất
- `predicted_bucket_end` là mốc kết thúc của bucket tương lai mà mô hình đang dự báo

## 10. Cách log thô trở thành gói dữ liệu đặc trưng

Quá trình chuyển đổi này chính là trái tim của `v2`.

Quy trình là:

1. nhận các sự kiện thô từ Kafka
2. chuẩn hóa chúng thành một sơ đồ sự kiện ổn định
3. thêm chúng vào trạng thái gần đây
4. cắt tỉa trạng thái theo thời gian lưu giữ cần thiết cho các cửa sổ và đường cơ sở
5. tính toán các cửa sổ bot hiện tại từ các sự kiện thực thể gần đây
6. tính toán các cửa sổ bất thường hiện tại từ các sự kiện endpoint gần đây
7. cập nhật các nhóm dự báo từ thời gian các sự kiện gần đây
8. xây dựng các gói dữ liệu cụ thể cho từng nhiệm vụ từ các tổng hợp đó
9. gửi các gói dữ liệu tới ML API
10. hợp nhất các dự đoán trở lại vào các hàng dữ liệu của ClickHouse

Tóm lại:

- log thô là dữ liệu sự kiện
- các cửa sổ là dữ liệu phái sinh
- các gói dữ liệu ML là dữ liệu đặc trưng (features)
- các dự đoán là dữ liệu đầu ra

## 11. Cơ chế cửa sổ Spark trong dự án này (Spark windowing in this project)

Spark được sử dụng làm engine mặc định cho việc xây dựng cửa sổ đặc trưng.

Spark session được khởi tạo **một lần duy nhất** (singleton pattern) và tái sử dụng giữa các batch. Điều này tránh overhead của việc khởi động JVM mỗi lần xử lý.

Spark được sử dụng để:

- gom nhóm các bản ghi thành các cửa sổ thời gian theo entity/endpoint
- tổng hợp số lượng, giá trị trung bình và ước tính phân vị
- xử lý song song trên nhiều cores (local[2])

Lưu ý quan trọng:

Spark không thay thế logic poll Kafka.
Kafka vẫn cung cấp các nhóm thu nạp dữ liệu (ingestion batches).
Spark được sử dụng *sau khi* thu nạp để tính toán các cửa sổ đặc trưng.

Vì vậy, mối quan hệ là:

- Kafka đưa ra nhóm vận chuyển
- luồng lưu trữ trạng thái
- Spark tính toán các cửa sổ đặc trưng (singleton session, reused)
- ML nhận các gói dữ liệu đã được tổng hợp

## 12. Tại sao các gói dữ liệu phải cụ thể cho từng nhiệm vụ

Ba nhiệm vụ ML trả lời các câu hỏi khác nhau.
Chúng không nên chia sẻ một gói dữ liệu chung chung quá nhỏ bé.

### Phát hiện Bot quan tâm đến hành vi

Nó cần:

- định danh tác nhân (actor)
- tần suất yêu cầu
- sự lặp lại
- tính bùng nổ
- tỷ lệ phương thức
- tỷ lệ lỗi
- các mẫu user-agent đáng ngờ

### Dự báo quan tâm đến lịch sử theo thời gian

Nó cần:

- các lượt đếm lưu lượng truy cập trước đó
- xu hướng (trend)
- tính biến thiên (variability)
- ngữ cảnh giờ trong ngày và ngày trong tuần

### Phát hiện bất thường quan tâm đến sai lệch so với đường cơ sở

Nó cần:

- độ trễ hiện tại
- độ trễ ở đuôi (tail latency)
- tỷ lệ lỗi
- đường cơ sở bình thường gần đây

Đó là lý do tại sao `v2` chia các hợp đồng theo nhiệm vụ thay vì ép buộc một hình dạng yêu cầu chung.

## 13. Ví dụ: một nhóm NATS không bằng một cửa sổ

Giả sử `STREAM_BATCH_SIZE=5`.

Luồng thăm dò NATS và nhận được năm tin nhắn mới.
Điều đó không có nghĩa là mô hình bot chỉ nhìn thấy đúng năm yêu cầu đó.

Thay vào đó:

- năm yêu cầu đó được thêm vào `recent_events`
- `recent_events` có thể đã chứa các sự kiện cũ hơn từ 55 giây trước đó
- cửa sổ bot bây giờ có thể chứa 42 sự kiện cho một thực thể
- cửa sổ bất thường hiện tại có thể chứa 120 sự kiện cho một endpoint
- lịch sử dự báo có thể chứa 10 lượt đếm nhóm dữ liệu

Vì vậy, một nhóm vận chuyển nhỏ có thể cập nhật các cửa sổ phân tích lớn.

Đây chính xác là cách các hệ thống luồng dữ liệu (streaming systems) thường xuyên hoạt động.

## 14. Mô hình tư duy cuối cùng cho nhóm

Nếu nhóm chỉ nhớ một điều, thì đó nên là điều này:

- log thô không phải là đặc trưng ML (ML features)
- bộ xử lý luồng chịu trách nhiệm chuyển đổi sự kiện thành đặc trưng
- gom nhóm NATS chỉ dành cho vận chuyển tin nhắn
- cửa sổ (windows) và nhóm (buckets) mới là đơn vị phân tích thực sự
- ML nên tiêu thụ các gói dữ liệu đã được tổng hợp, không phải các sự kiện thô đơn lẻ

Đó là ý nghĩa của `v2` trong kho lưu trữ này.
