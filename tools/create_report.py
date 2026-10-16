"""Create the four-page Vietnamese lab report from captured evidence, not mockups."""
import json, pathlib, html, re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, Preformatted, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER
from PIL import Image as PILImage

ROOT=pathlib.Path(__file__).resolve().parents[1]
E=ROOT/'output/evidence'; OUT=ROOT/'output/pdf'; OUT.mkdir(exist_ok=True,parents=True)
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold',r'C:\Windows\Fonts\arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Consolas',r'C:\Windows\Fonts\consola.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='ArialBold',italic='Arial',boldItalic='ArialBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyVN',fontName='Arial',fontSize=9,leading=13,spaceAfter=7,textColor=colors.HexColor('#243B36')))
styles.add(ParagraphStyle(name='TitleVN',fontName='ArialBold',fontSize=24,leading=29,spaceAfter=10,textColor=colors.HexColor('#12695F')))
styles.add(ParagraphStyle(name='HeadVN',fontName='ArialBold',fontSize=13,leading=17,spaceBefore=9,spaceAfter=7,textColor=colors.HexColor('#12695F')))
styles.add(ParagraphStyle(name='SmallVN',fontName='Arial',fontSize=7.7,leading=10,spaceAfter=5))
styles.add(ParagraphStyle(name='CaptionVN',fontName='Arial',fontSize=8,leading=11,alignment=TA_CENTER,spaceAfter=7))
styles.add(ParagraphStyle(name='CodeVN',fontName='Consolas',fontSize=7,leading=9,spaceAfter=7))
story=[]
def p(text,style='BodyVN'): return Paragraph(text,styles[style])
def add(text,style='BodyVN'): story.append(p(text,style))
def head(text): add(text,'HeadVN')
def code(text): story.append(Preformatted(text,styles['CodeVN']))
def image(name,w,h):
    path=E/name
    iw,ih=PILImage.open(path).size; scale=min(w/iw,h/ih)
    return Image(str(path),width=iw*scale,height=ih*scale)
def detail(name,box,w,h):
    cropped=PILImage.open(E/name).crop(box)
    target=ROOT/'tmp/pdfs'/('detail-'+pathlib.Path(name).stem+'.png')
    target.parent.mkdir(parents=True,exist_ok=True); cropped.save(target)
    iw,ih=cropped.size; scale=min(w/iw,h/ih)
    return Image(str(target),width=iw*scale,height=ih*scale)
def table(rows,widths):
    cells=[[p(str(cell),'SmallVN') for cell in row] for row in rows]
    t=Table(cells,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E0EEEA')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#D7E2DE'))]))
    story.append(t)

add('EXERCISE 3','SmallVN')
add('Giám sát nhiệt độ, độ ẩm<br/>và cảnh báo Firebase','TitleVN')
add('Báo cáo triển khai và kiểm chứng | 16/10/2026 | Android Java + XML','SmallVN')
head('1. Mục tiêu và phạm vi hoàn thành')
add('Mở rộng ứng dụng giám sát môi trường để nhận đồng thời Temperature, Humidity, Mode, Threshold và Timestamp từ Firebase Realtime Database. Giao diện hiển thị dữ liệu trực tiếp; người dùng có thể bật/tắt cảnh báo và điều chỉnh ngưỡng. Khi Mode bật và nhiệt độ lớn hơn ngưỡng, ứng dụng hiện đúng Toast yêu cầu và khởi động âm báo bằng MediaPlayer.')
add('Dự án ban đầu chỉ có màn hình Compose “Hello Android”, chưa có Firebase. Bản triển khai chuyển sang MainActivity.java và activity_main.xml theo đề; bổ sung SDK, quyền Internet, âm thanh WAV, kiểm tra dữ liệu và các bài kiểm thử.')
table([['Thành phần','Cấu hình sử dụng'],['Android','Package com.example.lab2_firebase_connectedmonitoringapp; minSdk 24; compile/target 37; máy ảo API 37'],['Firebase SDK','BoM 34.7.0; firebase-database; Material Components 1.13.0'],['Cloud','lab-2-connected-monitoring-app; Singapore; rules khóa theo lựa chọn người dùng'],['Kiểm thử chức năng','Firebase RTDB Emulator chính thức v4.11.2 trên 127.0.0.1:9000; Android truy cập qua 127.0.0.1 (ADB reverse)']], [92,415])
head('2. Cấu trúc dữ liệu và cách đồng bộ')
code('Config/Latest\n  Temperature: 27.5       // number, Celsius\n  Humidity:    65.0       // number, %RH, 0..100\n  Mode:        true       // boolean (UI also reads legacy 0/1)\n  Threshold:   30         // number, -50..100 Celsius\n  Timestamp:   <epoch ms> // timestamp from sensor / publisher')
add('setupListeners() gắn một ValueEventListener tại Config/Latest. Mỗi snapshot được đọc và kiểm tra trước khi cập nhật TextView/SwitchMaterial; log in đủ năm trường bằng tag FirebaseMonitor. Listener .info/connected phản ánh kết nối. Trường thiếu/sai kiểu không bị thay bằng số 0 gây hiểu nhầm: giao diện báo lỗi hoặc chờ dữ liệu, đồng thời khóa điều khiển.')
add('Nút +/− gọi runTransaction() trên Threshold với bước 1 °C, tránh mất lượt tăng khi nhiều client cùng sửa. Mode ghi bằng setValue(); render dùng cờ rendering để cập nhật switch từ server mà không tạo vòng lặp ghi. Listener được tháo tại onStop(), MediaPlayer được giải phóng khi hoàn tất hoặc rời màn hình.')
story.append(detail('firebase-cloud-data.jpg',(100,340,600,570),400,160))
add('Chi tiết Config/Latest trên cloud; ảnh Console đầy đủ: firebase-cloud-data.jpg.','CaptionVN')

story.append(PageBreak())
add('Giao diện và logic cảnh báo','TitleVN')
head('3. Giao diện chạy thực tế trên Android Emulator')
imgs=Table([[image('01-normal.png',235,345),image('03-high-toast.png',235,345)]],colWidths=[253.5,253.5])
story.append(imgs)
table([['Hình 1 - Bình thường','Hình 2 - Vượt ngưỡng'],['27.5 °C; độ ẩm 65%; Threshold 30 °C; Mode ON. Nhãn LOCAL Firebase Emulator thể hiện môi trường thử nghiệm.','Cập nhật Firebase cục bộ thành 36.5 °C và 72%. Màn hình đổi số liệu, báo HIGH TEMPERATURE và hiện Toast cảnh báo.']], [253.5,253.5])
head('4. Điều kiện kích hoạt và quản lý âm thanh')
code('boolean high = dataReady\n    && MonitorState.isHigh(temperature, threshold, mode);\nif (high && !wasHigh && connected) notifyHighTemperature();\nwasHigh = high && connected;\n\n// MonitorState.isHigh():\nreturn mode && temperature != null && threshold != null\n       && temperature > threshold;')
add('So sánh dùng dấu &gt;: nhiệt độ bằng Threshold vẫn bình thường. Cờ wasHigh chỉ cho phát cảnh báo khi đi vào trạng thái cao; thay đổi độ ẩm trong lúc nhiệt độ vẫn cao không phát lặp. Hạ nhiệt hoặc tắt Mode sẽ kết thúc trạng thái cao; bật lại Mode khi còn vượt ngưỡng kích hoạt cảnh báo mới.')
add('notifyHighTemperature() hiện Toast “Warning: Temperature exceeds threshold!” và phát res/raw/alert_tone.wav bằng MediaPlayer, dùng AudioAttributes cho âm thông báo. WAV được đóng gói trong APK nên không phụ thuộc âm mặc định của thiết bị. Log ghi “Notification sound started”; âm lượng và chế độ im lặng của thiết bị vẫn quyết định khả năng nghe thực tế.')

story.append(PageBreak())
add('Kiểm thử và LogCat','TitleVN')
head('5. Phương pháp kiểm chứng')
add('tools/verify_app.py chạy APK thật trên máy ảo Android. Script cập nhật Firebase Emulator qua REST, đọc cây UI bằng UI Automator, bấm nút bằng ADB, kiểm tra dữ liệu đã ghi trở lại database và chụp ảnh từ screencap. Không dùng ảnh dựng và không ghi thử lên database cloud.')
results=json.loads((E/'test-results.json').read_text(encoding='utf-8'))
names=[('Realtime temperature and humidity','Đọc nhiệt độ và độ ẩm thời gian thực'),('Increase threshold writes to Firebase','Tăng Threshold và xác nhận giá trị database'),('Decrease threshold writes to Firebase','Giảm Threshold và xác nhận giá trị database'),('Threshold exceeded: Toast and MediaPlayer started','Vượt ngưỡng: Toast, log và MediaPlayer'),('Repeated high snapshot does not repeat alert','Không lặp cảnh báo khi chỉ đổi độ ẩm'),('Mode OFF persisted and pauses alerts','Mode OFF ghi database và dừng cảnh báo'),('Mode ON rearms warning while high','Mode ON kích hoạt lại khi nhiệt độ cao'),('Equality does not trigger warning','Nhiệt độ bằng ngưỡng không cảnh báo'),('Invalid humidity disables controls without crashing','Độ ẩm sai kiểu: báo dữ liệu lỗi, khóa nút'),('Upper threshold bound disables increase','Ngưỡng 100: khóa nút tăng'),('Lower threshold bound disables decrease','Ngưỡng -50: khóa nút giảm'),('Locked database reports Permission denied','Rules khóa: hiện Permission denied'),('Activity restart restores data and listeners','Mở lại Activity nhận lại dữ liệu')]
lookup={r['test']:r['result'] for r in results}
table([['#','Kịch bản','Kết quả']]+[[i+1,label,lookup.get(key,'CHƯA XÁC NHẬN')] for i,(key,label) in enumerate(names)], [25,407,75])
head('6. Trích LogCat thực thu thập')
log=(E/'logcat.txt').read_text(encoding='utf-8',errors='replace')
selected=[]
for line in log.splitlines():
    if any(s in line for s in ['Temperature=36.5','ALERT:','Notification sound started','Mode committed','Threshold committed','Permission denied']):
        # Keep message, omit volatile PID/time prefix, then wrap for readability.
        message=re.split(r'FirebaseMonitor\s*:\s*',line)[-1]
        import textwrap
        selected.extend(textwrap.wrap(message,width=98,subsequent_indent='  '))
code('\n'.join(selected[:13]))
add('Build APK thành công; 4 unit tests qua (3 ca MonitorState và 1 ca mẫu); lint: 0 lỗi, 44 cảnh báo (gồm chuỗi viết trực tiếp và phiên bản thư viện). Log đầy đủ: output/evidence/logcat.txt; kết quả: test-results.json; log build: output/build-validation.log. Các ảnh 05-08 bổ sung minh chứng cho bảng kiểm thử.','SmallVN')
add('Giới hạn bằng chứng: ảnh tĩnh không chứng minh âm thanh nghe được. Kiểm thử xác nhận MediaPlayer đã khởi động và không có lỗi âm thanh được ghi; cần nghe trực tiếp trên thiết bị nếu yêu cầu nghiệm thu phần cứng. Cảm biến trong báo cáo là dữ liệu mẫu được cập nhật qua REST, chưa phải cảm biến vật lý.','SmallVN')

story.append(PageBreak())
add('Firebase cloud và đánh giá','TitleVN')
head('7. Cấu hình cloud được giữ khóa')
story.append(detail('firebase-rules-locked.jpg',(95,298,620,415),507,130))
add('Hình 3 - Chi tiết rules cloud khóa; ảnh Console đầy đủ: firebase-rules-locked.jpg.','CaptionVN')
add('Ứng dụng Android đã đăng ký App ID 1:395007766022:android:c98127f7abf93b30da1d87; database cloud tại Singapore đã có dữ liệu mẫu. Kiểm tra APK với cloud thật ghi .info/connected=true, sau đó đọc Config/Latest trả “Permission denied”, đúng với lựa chọn giữ rules khóa. Minh chứng: 10-cloud-locked.png và cloud-app-logcat.txt. Không có kết quả đọc/ghi dữ liệu cloud thành công được báo cáo; 13 ca chức năng sử dụng Firebase Emulator cục bộ.')
add('firebase_config.xml chứa định danh ứng dụng đã đối chiếu Console và database URL. FirebaseInitProvider khởi tạo ứng dụng từ resources; không cần tệp google-services.json cho cấu hình RTDB thủ công này. Bản debug chỉ dùng emulator khi được khởi chạy với extra localEmulator=true; bản release bỏ qua cờ đó. Ngoại lệ HTTP chỉ tồn tại ở debug và chỉ cho địa chỉ 127.0.0.1 (ADB reverse).')
head('8. Tái hiện và đối chiếu mã nguồn')
code('.\\gradlew.bat assembleDebug testDebugUnitTest lintDebug\nadb install -r app/build/outputs/apk/debug/app-debug.apk\n# Start the official RTDB emulator locally on port 9000.\n# Seed local rules/data, launch debug app and verify:\npython tools/verify_app.py')
add('MainActivity.java: setupListeners(), changeThreshold(), render(), notifyHighTemperature() và vòng đời. MonitorState.java: xác thực số, phép so sánh và giới hạn ngưỡng. activity_main.xml: TextView, SwitchMaterial và hai MaterialButton. Hướng dẫn đầy đủ, lệnh chạy emulator, sơ đồ dữ liệu và danh mục bằng chứng nằm trong README.md.','SmallVN')
head('9. Nhận xét và hướng phát triển')
add('Realtime Database phù hợp minh họa IoT vì publisher thay đổi một node và listener tự cập nhật giao diện, không cần polling. Điểm cần chú ý là dữ liệu phải đúng kiểu, timestamp phải thống nhất đơn vị, trạng thái offline phải rõ và lệnh ghi phải xử lý bất đồng bộ. Transaction giải quyết xung đột Threshold; cờ trạng thái ngăn chuỗi snapshot tạo âm báo liên tục.')
add('Phạm vi hiện tại là cảnh báo khi màn hình hoạt động, chưa có dịch vụ nền hoặc push notification. Hướng phát triển là xác thực người dùng/thiết bị, rules theo quyền sở hữu, App Check, lưu lịch sử và biểu đồ, phát hiện dữ liệu quá cũ, thử nghiệm cảm biến thật và kiểm thử âm thanh trên điện thoại. Giữ cloud khóa đồng nghĩa cần thiết kế xác thực và rules phù hợp trước khi sử dụng cloud với client.')
add('Tài liệu: Đề Exercise3-EnhancingFirebaseMonitoringApp.pdf; Firebase Android Read and Write Data; Connect your app to the Realtime Database Emulator. Truy cập 16/10/2026.<br/>https://firebase.google.com/docs/database/android/read-and-write<br/>https://firebase.google.com/docs/emulator-suite/connect_rtdb','SmallVN')

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#D7E2DE')); canvas.line(44,36,551,36)
    canvas.setFont('Arial',8); canvas.setFillColor(colors.HexColor('#536762'))
    canvas.drawString(44,24,'EXERCISE 3 | FIREBASE MONITORING | 16.10.2026')
    canvas.drawRightString(551,24,f'{doc.page} / 4')
doc=SimpleDocTemplate(str(OUT/'Exercise3-Report-VI.pdf'),pagesize=(595.28,841.89),rightMargin=44,leftMargin=44,topMargin=34,bottomMargin=47,title='Exercise 3 - Firebase Monitoring - Báo cáo triển khai',author='Exercise 3 Project')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT/'Exercise3-Report-VI.pdf')

