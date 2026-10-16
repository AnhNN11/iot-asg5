# Exercise 3 - Firebase Monitoring App

Ứng dụng Android Java/XML theo Exercise 3: đọc nhiệt độ và độ ẩm, hiển thị Mode/Threshold, tăng giảm ngưỡng, Toast và âm báo khi vượt ngưỡng.

## Trạng thái cloud và môi trường kiểm thử

Người dùng yêu cầu **giữ database cloud khóa**. Firebase Console đã đăng ký ứng dụng Android, tạo Realtime Database tại Singapore và nhập dữ liệu mẫu. Rules cloud giữ nguyên `.read: false`, `.write: false`; bản rules mở thử nghiệm đã bị hủy, không Publish.

Các ca kiểm thử chức năng dùng **Firebase Realtime Database Emulator chính thức v4.11.2**, kết hợp Android Emulator API 37 và APK thật. Giao diện thử nghiệm hiển thị nhãn `LOCAL Firebase Emulator`. Không xem các ảnh này là minh chứng client cloud đọc/ghi thành công. Cloud client không có quyền đọc/ghi với cấu hình khóa hiện tại. Muốn dùng cloud cần bổ sung Firebase Authentication và rules theo quyền sở hữu hoặc một cơ chế cấp quyền được người dùng chấp thuận.

Đã kiểm tra APK với cloud thật: `.info/connected=true`, đọc `Config/Latest` bị `Permission denied`, không có thao tác ghi cloud từ app. Ảnh `output/evidence/10-cloud-locked.png` và log `cloud-app-logcat.txt` minh chứng. REST đọc cloud không xác thực cũng trả HTTP 401 với `Permission denied` trong `cloud-read-check.txt`.

## Cấu trúc và chức năng

| Tệp | Vai trò |
|---|---|
| `app/src/main/java/com/example/lab2_firebase_connectedmonitoringapp/MainActivity.java` | Khởi tạo UI, listener, transaction, ghi Mode, cảnh báo và vòng đời |
| `app/src/main/java/com/example/lab2_firebase_connectedmonitoringapp/MonitorState.java` | Xác thực số, so sánh nhiệt độ và chặn giới hạn Threshold |
| `app/src/main/res/layout/activity_main.xml` | TextView cho Temperature/Humidity/Threshold/Timestamp, SwitchMaterial cho Mode, MaterialButton +/− |
| `app/src/main/res/values/firebase_config.xml` | App ID đã đối chiếu Console, project ID, sender ID và URL database |
| `app/src/main/res/raw/alert_tone.wav` | Âm báo đóng gói trong APK, không phụ thuộc âm hệ thống |
| `app/src/debug/` | Ngoại lệ HTTP chỉ cho địa chỉ emulator 127.0.0.1 (ADB reverse) |
| `database.rules.json` | Rules cloud khóa, phản ánh lựa chọn người dùng |
| `tools/emulator.rules.json` | Rules dùng riêng cho emulator loopback cục bộ |
| `tools/verify_app.py` | Kiểm thử APK thật, ghi kết quả và chụp màn hình |
| `tools/create_report.py` | Tạo báo cáo PDF tiếng Việt từ bằng chứng đã thu thập |

### Dữ liệu

```json
{
  "Config": {
    "Latest": {
      "Temperature": 27.5,
      "Humidity": 65.0,
      "Mode": true,
      "Threshold": 30,
      "Timestamp": 1792120500000
    }
  }
}
```

Tên trường phân biệt hoa thường. Temperature dùng °C; Humidity dùng %RH; Timestamp dùng Unix epoch **mili giây**. Ứng dụng cũng hiển thị timestamp dạng chuỗi từ publisher cũ, nhưng dữ liệu mẫu và kiểm thử dùng epoch ms. Mode chuẩn là boolean; listener tương thích số 0/1 của dữ liệu Lab 2 cũ, còn thao tác switch luôn ghi boolean.

`setupListeners()` đăng ký một listener tại `Config/Latest`, nên các trường được xử lý từ cùng snapshot. `onDataChange()` đọc Temperature, Humidity, Mode, Threshold và Timestamp; kiểm tra kiểu dữ liệu; ghi LogCat với tag `FirebaseMonitor`; sau đó render UI. `.info/connected` cung cấp trạng thái kết nối. Không có dữ liệu hợp lệ thì UI không tự bịa giá trị mặc định: số thiếu hiển thị dấu gạch, trạng thái báo chờ dữ liệu và các điều khiển bị khóa.

Nhiệt độ hợp lệ nằm trong −50..150 °C, độ ẩm 0..100%, Threshold −50..100 °C. Các giới hạn là lựa chọn triển khai để tránh nút tăng/giảm vô hạn; đề không ấn định khoảng. Giá trị số nguyên và số thực đều được đọc dưới dạng Number, tránh lỗi ép Long/Double của Firebase.

### Ghi Threshold và Mode

Hai nút điều chỉnh Threshold theo bước 1 °C. `runTransaction()` đọc ngưỡng hiện tại trên Firebase rồi cộng/trừ, nên hai client thay đổi đồng thời không ghi đè dựa trên giá trị cũ. Callback transaction phân biệt lỗi, hủy giao dịch và commit thành công; `fireLocalEvents=false` tránh UI hiển thị giá trị thử nghiệm chưa commit của transaction. Tại 100 °C, nút tăng bị khóa; tại −50 °C, nút giảm bị khóa.

Switch ghi Mode bằng `setValue()`. Cờ `rendering` phân biệt cập nhật switch từ snapshot với thao tác của người dùng, tránh vòng lặp ghi. Cờ `writePending` khóa các thao tác điều khiển khác trong khi đợi Firebase xác nhận. Khi lỗi ghi xảy ra, Toast và LogCat ghi rõ thao tác cùng thông điệp lỗi.

### Cảnh báo

Điều kiện là dữ liệu hợp lệ, có kết nối, Mode ON và **Temperature > Threshold**. Bằng ngưỡng không cảnh báo. Toast đúng nội dung đề: `Warning: Temperature exceeds threshold!`. MediaPlayer phát WAV với AudioAttributes loại thông báo; log ghi `Notification sound started`. MediaPlayer được release khi hoàn tất, khi lỗi và tại onStop.

`wasHigh` phát hiện chuyển trạng thái: chỉ thay đổi Humidity khi Temperature vẫn cao không phát lại âm thanh. Hạ nhiệt xuống bằng hoặc dưới ngưỡng sẽ cho phép cảnh báo ở lần vượt tiếp theo. Tắt Mode kết thúc trạng thái cao; bật lại Mode trong lúc còn cao tạo cảnh báo mới. Cơ chế này áp dụng trong phiên màn hình hoạt động; mở lại Activity có thể cảnh báo lại nếu vẫn cao.

Ứng dụng tháo listener tại onStop và gắn lại tại onStart. Đây là cảnh báo khi UI hoạt động, không phải dịch vụ giám sát nền hay FCM push notification.

## Build và chạy

Yêu cầu: Android SDK 37, JDK tương thích Gradle 9.6/AGP 9.4.1; máy này dùng JBR 25 của Android Studio. Không cần tài khoản Firebase để chạy emulator.

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
.\gradlew.bat assembleDebug testDebugUnitTest lintDebug --max-workers=2
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r app/build/outputs/apk/debug/app-debug.apk
```

FirebaseInitProvider khởi tạo Firebase từ resources trong `firebase_config.xml`. Cấu hình RTDB thủ công này dùng App ID và database URL; không cần Google Services Gradle plugin hoặc google-services.json. Không có khóa quản trị hay credential server trong ứng dụng. Cấu hình này không bật Authentication, Analytics hay dịch vụ Firebase khác.

Mở ứng dụng bình thường dùng database cloud và sẽ hiện Permission denied vì rules đang khóa. Để thử đầy đủ mà giữ cloud khóa:

```powershell
# Khởi chạy máy ảo có sẵn nếu cần:
& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone_API_37.0

# Tải JAR chính thức nếu thiếu, xác minh SHA-256 rồi chạy loopback :9000:
.\tools\start-emulator.ps1

# Dùng Python có sẵn trên máy; script chỉ cần thư viện chuẩn:
python tools/verify_app.py
```

`start-emulator.ps1` chạy tiến trình ẩn và in PID. Dừng bằng `Stop-Process -Id <PID đã in>`. Dữ liệu emulator là tạm thời và được seed lại bởi script kiểm thử. Nếu cổng 9000 đã có emulator đang chạy, dùng tiến trình đó, không khởi động trùng.

Khởi chạy thủ công chế độ local (chỉ có hiệu lực trên build DEBUG):

```powershell
adb reverse tcp:9000 tcp:9000
adb shell am force-stop com.example.lab2_firebase_connectedmonitoringapp
adb shell am start -n com.example.lab2_firebase_connectedmonitoringapp/.MainActivity --ez localEmulator true
```

`firebase.json` cũng cho phép dùng Firebase CLI nếu đã cài: `firebase emulators:start --only database --project demo-exercise3`. Namespace của bộ kiểm thử: `demo-exercise3-default-rtdb`. Không dùng lệnh deploy rules lên cloud khi chưa được người dùng đồng ý.

## Kiểm thử và bằng chứng

Unit test trong MonitorStateTest kiểm tra: vượt/bằng/dưới ngưỡng, Mode OFF, giá trị null, sai kiểu, NaN/Infinity và giới hạn tăng giảm. Kiểm thử tích hợp kiểm tra luồng Firebase SDK thực với backend emulator, UI thật và giá trị đã được ghi trở lại database.

`tools/verify_app.py` chạy 13 ca: đọc nhiệt độ/độ ẩm; tăng; giảm; cảnh báo vượt ngưỡng; chống lặp; Mode OFF; Mode ON; bằng ngưỡng; dữ liệu độ ẩm sai; cận trên; cận dưới; rules khóa; khởi động lại Activity. Các ca không chỉ so sánh hàm với chính nó: script có REST write/read, UI hierarchy assertions và đối chiếu số lần xuất hiện ALERT trong LogCat.

Kết quả cuối cùng được ghi trong `output/evidence/test-results.json`; chỉ những ca đã qua mới được đánh dấu PASS. `output/build-validation.log` là log build/unit tests/lint. `output/evidence/logcat.txt` chứa log thu trực tiếp từ Android, không phải log ví dụ tự viết.

Ảnh `01-normal.png` là trạng thái bình thường; `02-threshold-increased.png` chứng minh tăng ngưỡng; `03-high-toast.png` ghi cảnh báo Toast; `04-high-temperature.png` ghi trạng thái nhiệt độ cao; `05-mode-off.png` ghi Mode OFF; `06-equal-threshold.png` kiểm tra bằng ngưỡng; `07-invalid-humidity.png` ghi dữ liệu sai; `08-permission-denied.png` ghi rules từ chối; `09-final-normal.png` ghi trạng thái sau mở lại Activity. `firebase-rules-locked.jpg` là ảnh Console cloud thật.

Ảnh tĩnh không chứng minh âm thanh nghe được. Log xác nhận MediaPlayer.start() chạy; khả năng nghe phụ thuộc âm lượng, chế độ thiết bị và đường âm thanh của Android Emulator. Chưa có thử nghiệm cảm biến vật lý hoặc điện thoại thật. Kiểm thử local không thay thế kiểm thử quyền Authentication/App Check của cloud.

## Báo cáo và hướng phát triển

`output/pdf/Exercise3-Report-VI.pdf` là báo cáo 4 trang với mục tiêu, môi trường, giải thích code/schema, ảnh ứng dụng, bảng kiểm thử, LogCat, ảnh Firebase rules và nhận xét. Script tạo báo cáo dùng ReportLab, Pillow và font Arial/Consolas của Windows. Nội dung khẳng định kết quả căn cứ vào file evidence hiện có.

Hướng phát triển: Authentication và rules theo chủ sở hữu; phân quyền publisher cảm biến và người dùng điều khiển; App Check; lưu lịch sử, biểu đồ và lọc thời gian; phát hiện dữ liệu quá cũ; dịch vụ nền hoặc FCM nếu cần cảnh báo khi không mở UI; kiểm thử trực tiếp âm thanh và cảm biến vật lý.

Tài liệu tham khảo: https://firebase.google.com/docs/database/android/read-and-write và https://firebase.google.com/docs/emulator-suite/connect_rtdb; đề Exercise3-EnhancingFirebaseMonitoringApp.pdf do người dùng cung cấp.

