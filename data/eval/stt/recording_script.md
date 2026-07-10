# STT recording script

Record each utterance as one file (wav/m4a, quiet room + one noisy-room
repeat if possible; elderly speakers preferred). Name files by ID.
Then build `manifest.json`:

```json
[{"audio": "data/eval/stt/recordings/mw_grill_1.wav",
  "reference_vi": "Làm sao để nướng gà?", "case_id": "mw_grill_1"}]
```

| file | utterance |
|---|---|
| mw_grill_1.wav | Làm sao để nướng gà? |
| mw_grill_2.wav | Nuong banh mi cho gion thi bam nut nao? |
| mw_grill_3.wav | Tôi muốn nướng cá thu |
| mw_grill_4.wav | Chế độ nướng của lò dùng như thế nào? |
| mw_defrost_1.wav | Tôi muốn rã đông thịt đông lạnh |
| mw_defrost_2.wav | Ra dong ca bam nut gi? |
| mw_defrost_3.wav | Thịt để ngăn đá cứng quá, làm mềm nhanh được không? |
| mw_defrost_4.wav | Rã đông 500 gam thịt bò thì làm sao? |
| mw_reheat_1.wav | Hâm nóng cơm thế nào? |
| mw_reheat_2.wav | Hâm lại thức ăn nguội trong tủ lạnh |
| mw_reheat_3.wav | Ham nong chao cho nong lai |
| mw_reheat_4.wav | Hâm sữa cho cháu uống thì bấm nút nào? |
| mw_auto_menu_1.wav | Dùng chương trình nấu tự động như thế nào? |
| mw_auto_menu_2.wav | Lò có sẵn món nấu tự động không, chọn ở đâu? |
| mw_auto_menu_3.wav | Nau tu dong mon rau cu |
| mw_combination_1.wav | Nấu kết hợp vừa nướng vừa vi sóng được không? |
| mw_combination_2.wav | Chế độ kết hợp dùng khi nào? |
| mw_combination_3.wav | Muốn gà vừa chín bên trong vừa vàng da bên ngoài thì chọn chế độ gì? |
| mw_power_1.wav | Chọn công suất vi sóng ở đâu? |
| mw_power_2.wav | Giảm công suất xuống mức thấp để nấu liu riu |
| mw_power_3.wav | Chon muc cong suat lo vi song |
| mw_quick30_1.wav | Nấu nhanh 30 giây làm sao? |
| mw_quick30_2.wav | Cài nhanh từng 30 giây một thì bấm gì? |
| mw_quick30_3.wav | Chi can quay nong 30 giay thoi |
| mw_timer_1.wav | Cách hẹn giờ trên lò vi sóng? |
| mw_timer_2.wav | Dùng lò làm đồng hồ đếm giờ trong bếp được không? |
| mw_timer_3.wav | Cài đồng hồ của lò về 7 giờ sáng |
| mw_time1min_1.wav | Tăng thêm 1 phút nấu |
| mw_time1min_2.wav | Cài thời gian nấu 3 phút thì bấm sao? |
| mw_time10min_1.wav | Cộng thêm 10 phút vào thời gian nấu |
| mw_time10min_2.wav | Muốn nấu lâu 20 phút thì cài thế nào? |
| mw_time10sec_1.wav | Thêm 10 giây nữa thôi |
| mw_addtime_1.wav | Đồ ăn chưa chín, cộng thêm thời gian đang nấu được không? |
| mw_addtime_2.wav | Nut Add Time dung de lam gi? |
| mw_stop_1.wav | Làm sao dừng lò lại? |
| mw_stop_2.wav | Lò đang chạy, tôi muốn tắt ngay |
| mw_stop_3.wav | Bấm nhầm rồi, xoá cài đặt đi làm lại |
| mw_stop_4.wav | Dung lo lai gap |
| mw_start_1.wav | Cài xong rồi thì bấm gì để lò chạy? |
| mw_start_2.wav | Bắt đầu nấu đi |
| mw_start_3.wav | Nut khoi dong lo o dau? |
| mw_up_1.wav | Chỉnh thời gian tăng lên chút xíu |
| mw_down_1.wav | Lỡ cài nhiều quá, giảm thời gian xuống |
| mw_multi_grill_time.wav | Nướng trong 10 phút thì bấm những nút nào? |
| mw_multi_defrost_grill.wav | Cá đông lạnh, muốn rã đông xong nướng luôn |
| el_program_1.wav | Chọn chương trình giặt nhanh 15 phút thì làm sao? |
| el_program_2.wav | Giặt đồ len thì vặn núm về đâu? |
| el_program_3.wav | Muốn giặt chăn mền dày thì chọn chế độ nào? |
| el_program_4.wav | Giat do the thao thi chon o dau? |
| el_temp_1.wav | Chỉnh nhiệt độ nước giặt ở đâu? |
| el_temp_2.wav | Giặt nước nóng 60 độ cho sạch khuẩn |
| el_temp_3.wav | Doi sang giat nuoc lanh |
| el_power_1.wav | Bật máy giặt lên như thế nào? |
| el_power_2.wav | Tắt nguồn máy giặt đi |
| el_power_3.wav | Nut nguon o cho nao? |
| el_spin_1.wav | Muốn đổi tốc độ vắt thì bấm nút nào? |
| el_spin_2.wav | Vắt nhẹ thôi cho đồ đỡ nhăn |
| el_spin_3.wav | Chinh vong vat 800 vong |
| el_vapour_1.wav | Thêm hơi nước để diệt khuẩn quần áo |
| el_vapour_2.wav | Chế độ hơi nước Vapour bật ở đâu? |
| el_prewash_1.wav | Bật chế độ giặt sơ trước |
| el_prewash_2.wav | Áo bẩn nhiều bùn đất, muốn máy giặt sơ một lần trước khi giặt chính |
| el_prewash_3.wav | Giat so bat the nao? |
| el_rinse_1.wav | Tôi muốn máy xả thêm nước cho sạch xà phòng |
| el_rinse_2.wav | Da cháu bị dị ứng bột giặt, làm sao xả kỹ hơn? |
| el_rinse_3.wav | Bat xa them Extra Rinse |
| el_start_1.wav | Máy đang giặt mà muốn thêm quần áo thì làm sao? |
| el_start_2.wav | Chọn xong chương trình rồi, bấm gì để máy bắt đầu giặt? |
| el_start_3.wav | Tạm dừng máy giặt lại một chút |
| el_start_4.wav | Lo bo sot cai ao, mo cua bo them vao duoc khong? |
| el_timemgr_1.wav | Rút ngắn thời gian giặt lại được không? |
| el_timemgr_2.wav | Điều chỉnh thời gian giặt Time Manager dùng sao? |
| el_delay_1.wav | Hẹn giờ giặt xong sau 3 tiếng nữa |
| el_delay_2.wav | Muốn máy giặt xong đúng lúc tôi đi chợ về |
| el_delay_3.wav | Hen gio ket thuc o dau? |
| el_display_1.wav | Màn hình máy giặt đang hiển thị gì vậy? |
| ts_quick_1.wav | Tôi muốn giặt nhanh |
| ts_quick_2.wav | Giat nhanh do it ban |
| ts_dry_1.wav | Sấy quần áo thì bấm nút nào? |
| ts_dry_2.wav | Trời mưa đồ không khô, dùng chế độ sấy được không? |
| ts_start_1.wav | Bấm gì để máy bắt đầu giặt? |
| ts_start_2.wav | Tạm dừng máy một lát |
| dk_temp_1.wav | Tăng nhiệt độ điều hòa lên |
| dk_temp_2.wav | Lạnh quá, cho ấm lên chút |
| dk_temp_3.wav | Tang nhiet do len 26 do |