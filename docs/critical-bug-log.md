# Nhật Ký Kiểm Thử & Trạng Thái Lỗi (QA Bug Log)

Tài liệu này ghi nhận trạng thái kiểm thử hệ thống và theo dõi các lỗi nghiêm trọng (Critical Bugs) ảnh hưởng đến luồng vận hành chính thức của ứng dụng SilverTech.

### Trạng thái kiểm thử tổng thể (Tính đến Sprint 5)
- **Mức độ nghiêm trọng cao (Blocker/Critical):** 0 lỗi.
- **Mức độ nghiêm trọng trung bình (Major/Minor):** 0 lỗi.
- Toàn bộ luồng nghiệp vụ cốt lõi (Nhận diện logo $\rightarrow$ Khớp mẫu thiết bị $\rightarrow$ Nhận diện giọng nói offline $\rightarrow$ Suy luận LLM Backend $\rightarrow$ Vẽ khung sáng AR) đã được kiểm thử tích hợp thành công trên các dòng máy thật (bao gồm phân hệ Mobile và Backend API).

### Lịch sử theo dõi và khắc phục
1. **Lỗi lệch ma trận Homography khi quét lệch góc:**
   - *Mô tả:* Khi chụp góc nghiêng, các nút ở xa logo bị chiếu lệch vị trí.
   - *Cách khắc phục:* Đã bổ sung bộ lọc phân bổ điểm khớp (Inlier Spread Check) và thuật toán tự căn chỉnh cục bộ (Local Button Snapping) bằng Template Matching. Đã kiểm thử hoạt động ổn định.
2. **Trễ từ khóa khi gọi LLM suy luận:**
   - *Mô tả:* LLM sinh câu trả lời quá dài và có nguy cơ ảo giác nút bấm.
   - *Cách khắc phục:* Bổ sung ràng buộc cứng trong System Prompt ép trả về JSON cấu trúc rút gọn, đồng thời viết hàm `validate_guidance_buttons` đối chiếu database tại backend.

*Ứng dụng hiện tại đạt trạng thái ổn định để nộp bài và nghiệm thu.*
