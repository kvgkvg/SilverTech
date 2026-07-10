# Hạn Chế Đã Biết (Known Limitations)

Hệ thống SilverTech hiện tại được thiết kế như một MVP (Sản phẩm khả dụng tối thiểu) phục vụ cho tập người dùng cao tuổi. Do đó, hệ thống có một số hạn chế về mặt kỹ thuật và phạm vi cần lưu ý:

### 1. Giới hạn về góc quét và môi trường ánh sáng (Computer Vision)
- **Độ cong bảng điều khiển:** Ma trận Homography 2D giả định bề mặt bảng điều khiển là phẳng (planar). Với các thiết bị có bảng điều khiển cong vát sâu hoặc ống kính bị méo rìa nặng, độ chính xác hình học của khung AR sáng có thể bị giảm nhẹ.
- **Nhiễu chói sáng (Glare):** Bề mặt kính bóng loáng của các thiết bị có thể phản chiếu ánh đèn LED hoặc đèn flash điện thoại, gây suy giảm số lượng điểm đặc trưng SIFT/ORB. Hệ thống đã có cơ chế tự động chuyển đổi sang thuật toán SIFT global homography để bù đắp, nhưng nếu độ chói quá lớn dẫn đến không tìm đủ 15 điểm inliers, hệ thống sẽ yêu cầu người dùng quét lại.

### 2. Sự phụ thuộc vào dữ liệu mẫu (Templates-dependent)
- Hệ thống hoạt động theo cơ chế khớp mẫu (Template Matching). Điều này đồng nghĩa với việc ứng dụng chỉ hỗ trợ nhận diện và hướng dẫn cho các dòng thiết bị đã được định nghĩa mẫu trước trong cơ sở dữ liệu.
- Mặc dù hệ thống đã hỗ trợ luồng đóng góp cộng đồng (Crowdsourcing) để mở rộng thiết bị, các mẫu mới gửi lên vẫn cần qua bước kiểm duyệt thủ công của quản trị viên để đảm bảo chất lượng hình ảnh và nhãn nút trước khi đưa vào luồng chính thức.

### 3. Phụ thuộc vào kết nối mạng cho tính năng Hướng dẫn nâng cao (LLM)
- Mặc dù nhận dạng giọng nói (STT) và đọc hướng dẫn (TTS) chạy hoàn toàn offline trên thiết bị di động, luồng xử lý suy luận ngữ cảnh và sinh hướng dẫn (LLM) vẫn cần kết nối internet để gửi yêu cầu đến server backend. Nếu mất mạng hoàn toàn, hệ thống sẽ tạm dừng luồng LLM và báo lỗi kết nối.

### 4. Hạn chế trên môi trường Web Demo
- Trình nhận dạng giọng nói ngoại tuyến (Sherpa-ONNX) được thiết kế nguyên bản cho thiết bị di động (Android). Khi chạy bản Web Demo trên trình duyệt Chrome, hệ thống tự động chuyển sang Web Speech API của trình duyệt — dịch vụ này yêu cầu kết nối mạng và chỉ hỗ trợ đầy đủ trên nhân Chromium.
