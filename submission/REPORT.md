# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:**
- **MSSV:**
- **Lớp:** K4-L3A
- **Repository URL:**
- **Commit SHA cuối:**
- **Challenge ID:**
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-<MSSV>`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Chưa đạt do TODO CP1 | 100/100 | Đủ schema, correlation, enrichment và PII scrub |
| `validate_dashboard.py` | Contract starter | 6/6 panel | Runtime UI đọc trực tiếp `data/logs.jsonl` |
| `pytest` | | 27 passed | Chạy trên source cuối |
| Số traces hợp lệ | 0 | 16 request trace đã tạo | Baseline, candidate, promote và rollback |
| Số PII leak | Có dữ liệu test trước scrub | 0 | Theo `validate_logs.py` |
| Latency P95 / TTFT P95 | | 1.911 ms / 50 ms | Cửa sổ dashboard lúc chụp evidence |
| Retrieval success rate | | 100% | Cửa sổ dashboard lúc chụp evidence |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware nhận `x-request-id` hoặc tạo `req-<8-hex>`, bind vào context, gắn vào `request.state` và trả lại cùng `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env` cùng latency, TTFT, token, cost, quality và tool status.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor scrub đệ quy chạy sau bước materialize exception/stack nhưng trước file writer và JSON renderer.
- **Cách kiểm chứng kết quả:** Unit test email/điện thoại/CCCD/thẻ và regression test opaque ID; `validate_logs.py` đạt 100/100 với 0 PII leak.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Workload dùng user hash `19dbfa74132f`, session `cp2-baseline`/`cp2-candidate` và correlation ID có prefix `req-ba5...`/`req-ca1...`.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` loại agent chứa child `retrieval` loại retriever và `fake-llm-generation` loại generation; generation có model, prompt reference, usage, total cost và TTFT.
- **Cách nối trace với log:** Cùng `correlation_id` được bind vào structured log và trace metadata; raw input/output không được capture, chỉ dùng preview đã scrub.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 — `baseline`, `production` sau rollback.
- **Version/label candidate:** v2 — `candidate`.
- **Trace ID của mỗi version:** baseline `88a3422d0fb37deba428a0acc8131fcd`; candidate `f1806c5adff8cb2afacc918cbe49d63d`; production v2 `4b3105177c6695f5b45a17caa8c3cf4e`; production sau rollback v1 `b01290e5c5339015c86dab5cd38aef83`.
- **Cách promote và rollback `production`:** `manage_prompts.py promote` chuyển production sang v2, chạy request kiểm chứng; `manage_prompts.py rollback` đưa production về v1. Trạng thái cuối: baseline v1, candidate v2, production v1.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `/dashboard` hiển thị latency P50/P95/P99 + TTFT, traffic, errors + retrieval success, cost, input/output tokens và quality trong 60 phút; refresh 30 giây, có đơn vị và threshold line. Evidence: `evidence/11-dashboard-overview.png`.
- **SLO và lý do chọn:** 99,5% request có response thành công trong ≤ 3.000 ms trên 28 ngày. Ngưỡng cao hơn baseline fake LLM nhưng đủ thấp để phát hiện `rag_slow` có ảnh hưởng người dùng.
- **Cách tính error budget:** `total_requests × (1 − 0,995)`. Ví dụ 100.000 request cho phép 500 request xấu; tương đương 201,6 phút trên cửa sổ 28 ngày nếu traffic đều.
- **Ba alert và runbook tương ứng:** latency P95 > 3.000 ms/10m, error rate > 2%/5m, quality < 0,75 hoặc retrieval success < 90%/15m; cả ba gửi Slack `#llmops-alerts`, có owner và runbook trong `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
