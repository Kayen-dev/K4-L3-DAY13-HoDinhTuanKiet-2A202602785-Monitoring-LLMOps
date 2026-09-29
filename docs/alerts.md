# Alert runbooks

Các alert dưới đây dựa trên triệu chứng người dùng hoặc SLO. Mỗi lần điều tra đi
theo chuỗi **Metrics → Logs → Traces**: xác định cửa sổ bất thường trên dashboard,
lấy `correlation_id` từ log liên quan, rồi mở trace cùng ID để khoanh vùng
retrieval hay generation.

<a id="alert-1"></a>
## Alert 1 — LLM response latency SLO breach

- **Severity:** critical
- **Duration:** 10 phút liên tục
- **Kênh thông báo:** Slack `#llmops-alerts`
- **Owner:** `llm-platform-oncall`
- **SLI/SLO:** P95 latency ≤ 3.000 ms; 99,5% request tốt trong cửa sổ 28 ngày.
- **Điều kiện:** `latency_p95_ms > 3000` trong 10 phút.
- **Ảnh hưởng:** người dùng chờ câu trả lời quá lâu, có thể retry và làm tăng tải.

Ba bước kiểm tra đầu tiên:

1. Xác nhận P50/P95/P99 và TTFT trên panel Latency để phân biệt tail latency với
   chậm toàn bộ request.
2. Lọc `response_sent` có `latency_ms > 3000`, lấy `correlation_id` và kiểm tra
   feature/model bị ảnh hưởng.
3. Mở trace cùng `correlation_id`, so sánh thời lượng child `retrieval` với
   `fake-llm-generation`.

**Mitigation tạm thời:** tắt incident `rag_slow` nếu đang diễn tập; giảm
concurrency hoặc chuyển traffic sang model/fallback ổn định. Chỉ đóng alert khi
P95 dưới ngưỡng đủ 10 phút.

<a id="alert-2"></a>
## Alert 2 — LLM request error rate high

- **Severity:** critical
- **Duration:** 5 phút liên tục
- **Kênh thông báo:** Slack `#llmops-alerts`
- **Owner:** `api-oncall`
- **SLI/SLO:** error rate ≤ 2%; request lỗi cũng tiêu thụ error budget của SLO.
- **Điều kiện:** `error_rate_pct > 2` trong 5 phút.
- **Ảnh hưởng:** người dùng nhận HTTP 500 hoặc không nhận được câu trả lời.

Ba bước kiểm tra đầu tiên:

1. Xem breakdown `error_type` và retrieval success trên panel Errors.
2. Lọc event `request_failed`, nhóm theo `feature`, `model` và `tool_name`, rồi
   lấy một `correlation_id` đại diện.
3. Mở trace tương ứng, kiểm tra trạng thái/error message của child observation
   đầu tiên bị lỗi.

**Mitigation tạm thời:** tắt `tool_fail` nếu đây là incident thực hành; dùng
fallback không retrieval cho feature cho phép, hoặc rollback phiên bản vừa phát
hành. Escalate cho owner của dependency nếu lỗi nằm ngoài API.

<a id="alert-3"></a>
## Alert 3 — LLM answer quality degraded

- **Severity:** warning
- **Duration:** 15 phút liên tục
- **Kênh thông báo:** Slack `#llmops-alerts`
- **Owner:** `llm-quality-oncall`
- **SLI/SLO:** quality trung bình ≥ 0,75 và retrieval success ≥ 90%.
- **Điều kiện:** `quality_score_avg < 0.75` hoặc
  `retrieval_success_rate_pct < 90` trong 15 phút.
- **Ảnh hưởng:** API vẫn trả 200 nhưng câu trả lời thiếu căn cứ hoặc không hữu ích.

Ba bước kiểm tra đầu tiên:

1. So sánh panel Quality với Retrieval success để biết suy giảm bắt đầu ở dữ
   liệu hay generation.
2. Nhóm request theo `prompt_version`, `feature` và `model`; lấy
   `correlation_id` của nhóm giảm mạnh nhất.
3. Mở trace, xác nhận prompt name/label/version và số tài liệu retrieval trước
   khi đánh giá output đã scrub.

**Mitigation tạm thời:** rollback label `production` về prompt baseline nếu suy
giảm trùng thời điểm promote; nếu retrieval success giảm, chuyển sang corpus
fallback và báo owner dữ liệu. Tiếp tục theo dõi ít nhất 15 phút sau mitigation.
