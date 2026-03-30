Báo Cáo Bàn Giao ML API
Đã hoàn thành tích hợp model thật cho 3 bài toán của ml-api: bot, forecast, anomaly.
1. Dataset và cách train
Bot
•	Dataset: web robot detection từ Zenodo, file simple_features.csv
•	Huấn luyện trên Colab bằng RandomForestClassifier
•	Input train là các feature hành vi:
•	NUMBER_OF_REQUESTS
•	TOTAL_DURATION
•	AVERAGE_TIME
•	REPEATED_REQUESTS
•	HTTP_RESPONSE_2XX
•	HTTP_RESPONSE_3XX
•	HTTP_RESPONSE_4XX
•	HTTP_RESPONSE_5XX
•	GET_METHOD
•	POST_METHOD
•	HEAD_METHOD
•	OTHER_METHOD
•	NIGHT
•	MAX_BARRAGE
•	Output train:
•	ROBOT
•	Cách dán nhãn:
•	dùng trực tiếp nhãn có sẵn trong dataset
•	ROBOT = 1 là bot
•	ROBOT = 0 là không phải bot
Forecast
•	Dataset: lấy trực tiếp từ Wikimedia Analytics API
•	Tiền xử lý trên Colab thành forecast_training_dataset.csv
•	Huấn luyện bằng RandomForestRegressor
•	Input train là:
•	history_rps_0..9
•	rolling_mean_5
•	rolling_std_5
•	hour_of_day
•	day_of_week
•	Output train:
•	target_next_rps
•	Cách dán nhãn:
•	không dán nhãn thủ công
•	target được tạo từ chuỗi thời gian
•	dùng bucket traffic kế tiếp làm nhãn dự đoán
Anomaly
•	Dataset: Microsoft Cloud Monitoring Dataset
•	Tiền xử lý trên Colab thành anomaly_training_dataset.csv
•	Huấn luyện bằng RandomForestClassifier
•	Input train là:
•	request_count
•	avg_latency_ms
•	p95_latency_ms
•	p99_latency_ms
•	status_5xx_ratio
•	baseline_avg_latency_ms
•	baseline_5xx_ratio
•	Output train:
•	target_is_anomaly
•	Cách dán nhãn:
•	dùng label anomaly từ dataset gốc
•	sau đó gom theo window
•	nếu trong window có điểm bất thường thì gán target_is_anomaly = 1, ngược lại là 0
2. Cách dùng API
GET /healthz
•	Mục đích:
•	kiểm tra service có đang chạy không
•	kiểm tra đang ở mock hay model
•	Response trả ra:
•	status
•	mode
•	tasks
POST /predict/bot
•	Request truyền vào:
•	feature_version
•	window_start
•	window_end
•	entity:
•	ip
•	session_id
•	user_agent
•	features:
•	number_of_requests
•	total_duration_s
•	average_time_ms
•	repeated_requests
•	http_response_2xx
•	http_response_3xx
•	http_response_4xx
•	http_response_5xx
•	get_method
•	post_method
•	head_method
•	other_method
•	night
•	max_barrage
•	Response trả ra:
•	is_bot
•	bot_score
•	model_version
POST /predict/forecast
•	Request truyền vào:
•	feature_version
•	bucket_end
•	target:
•	scope
•	endpoint
•	history_rps
•	features:
•	rolling_mean_5
•	rolling_std_5
•	hour_of_day
•	day_of_week
•	Response trả ra:
•	predicted_request_count
•	model_version
POST /predict/anomaly
•	Request truyền vào:
•	feature_version
•	window_start
•	window_end
•	entity:
•	endpoint
•	features:
•	request_count
•	avg_latency_ms
•	p95_latency_ms
•	p99_latency_ms
•	status_5xx_ratio
•	baseline_avg_latency_ms
•	baseline_5xx_ratio
•	Response trả ra:
•	is_anomaly
•	anomaly_score
•	model_version

