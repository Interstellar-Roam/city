import Foundation
import CoreLocation
import AMapLocationKit

// MARK: - 轨迹点记录
struct TrackPoint: Codable {
    let latitude: Double
    let longitude: Double
    let altitude: Double?
    let speed: Double?
    let course: Double?
    let timestamp: Date
    let horizontalAccuracy: Double?
    
    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

// MARK: - 路线记录服务
class RouteRecordingService: NSObject, ObservableObject {
    // 状态
    @Published var isRecording = false
    @Published var isPaused = false
    @Published var trackPoints: [TrackPoint] = []
    @Published var totalDistance: Double = 0
    @Published var currentSpeed: Double = 0
    @Published var elapsedTime: TimeInterval = 0
    @Published var elevationGain: Double = 0
    
    // 定位
    private let locationManager = AMapLocationManager()
    private let headingManager = CLLocationManager()
    
    // 计时
    private var timer: Timer?
    private var startTime: Date?
    private var pausedDuration: TimeInterval = 0
    private var lastPauseTime: Date?
    
    // 记录
    private var lastRecordedPoint: TrackPoint?
    private var lastAltitude: Double?
    private let minDistanceFilter: Double = 3.0  // 最小3米记录一个点
    
    // MARK: - 生命周期
    
    override init() {
        super.init()
        setupLocationManager()
    }
    
    private func setupLocationManager() {
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBestForNavigation
        locationManager.locationTimeout = 5
        locationManager.pausesLocationUpdatesAutomatically = false
        locationManager.allowsBackgroundLocationUpdates = true
        
        headingManager.delegate = self
        headingManager.headingFilter = 2
        headingManager.headingOrientation = .portrait
        headingManager.requestWhenInUseAuthorization()
    }
    
    // MARK: - 控制
    
    func startRecording() {
        isRecording = true
        isPaused = false
        trackPoints = []
        totalDistance = 0
        elevationGain = 0
        elapsedTime = 0
        pausedDuration = 0
        startTime = Date()
        lastRecordedPoint = nil
        lastAltitude = nil
        
        locationManager.startUpdatingLocation()
        headingManager.startUpdatingHeading()
        
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self = self, self.isRecording, !self.isPaused else { return }
            self.elapsedTime = Date().timeIntervalSince(self.startTime!) - self.pausedDuration
        }
        
        print("🎬 路线记录开始")
    }
    
    func pauseRecording() {
        isPaused = true
        lastPauseTime = Date()
        locationManager.stopUpdatingLocation()
        timer?.invalidate()
        print("⏸ 路线记录暂停")
    }
    
    func resumeRecording() {
        isPaused = false
        if let pauseTime = lastPauseTime {
            pausedDuration += Date().timeIntervalSince(pauseTime)
        }
        lastPauseTime = nil
        locationManager.startUpdatingLocation()
        
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self = self, self.isRecording, !self.isPaused else { return }
            self.elapsedTime = Date().timeIntervalSince(self.startTime!) - self.pausedDuration
        }
        print("▶️ 路线记录继续")
    }
    
    func stopRecording() -> TrackData? {
        isRecording = false
        isPaused = false
        locationManager.stopUpdatingLocation()
        headingManager.stopUpdatingHeading()
        timer?.invalidate()
        timer = nil
        
        guard !trackPoints.isEmpty else {
            print("⚠️ 没有记录到轨迹点")
            return nil
        }
        
        let trackData = TrackData(
            points: trackPoints,
            totalDistance: totalDistance,
            elevationGain: elevationGain,
            duration: Int(elapsedTime),
            startedAt: startTime ?? Date(),
            endedAt: Date()
        )
        
        print("🏁 路线记录结束，共 \(trackPoints.count) 个点，距离 \(String(format: "%.1f", totalDistance))m")
        return trackData
    }
    
    // MARK: - 处理定位数据
    
    private func processLocation(_ location: CLLocation) {
        guard isRecording, !isPaused else { return }
        
        // 过滤精度差的点
        guard location.horizontalAccuracy > 0, location.horizontalAccuracy < 30 else {
            print("⚠️ 定位精度差: \(location.horizontalAccuracy)m，跳过")
            return
        }
        
        let point = TrackPoint(
            latitude: location.coordinate.latitude,
            longitude: location.coordinate.longitude,
            altitude: location.altitude > 0 ? location.altitude : nil,
            speed: location.speed >= 0 ? location.speed : nil,
            course: location.course >= 0 ? location.course : nil,
            timestamp: Date(),
            horizontalAccuracy: location.horizontalAccuracy
        )
        
        // 距离过滤：与上一个点距离太近则跳过
        if let last = lastRecordedPoint {
            let distance = distanceBetween(last.coordinate, point.coordinate)
            if distance < minDistanceFilter {
                return
            }
            totalDistance += distance
        }
        
        // 海拔增益计算
        if let altitude = point.altitude, let lastAlt = lastAltitude {
            let gain = altitude - lastAlt
            if gain > 1.0 {  // 超过1米才算上升
                elevationGain += gain
            }
        }
        lastAltitude = point.altitude
        
        // 更新速度
        currentSpeed = location.speed >= 0 ? location.speed : 0
        
        trackPoints.append(point)
        lastRecordedPoint = point
    }
    
    private func distanceBetween(_ from: CLLocationCoordinate2D, _ to: CLLocationCoordinate2D) -> Double {
        let loc1 = CLLocation(latitude: from.latitude, longitude: from.longitude)
        let loc2 = CLLocation(latitude: to.latitude, longitude: to.longitude)
        return loc1.distance(from: loc2)
    }
    
    // MARK: - 格式化
    
    var formattedDistance: String {
        if totalDistance >= 1000 {
            return String(format: "%.2f km", totalDistance / 1000)
        } else {
            return String(format: "%.0f m", totalDistance)
        }
    }
    
    var formattedDuration: String {
        let hours = Int(elapsedTime) / 3600
        let minutes = (Int(elapsedTime) % 3600) / 60
        let seconds = Int(elapsedTime) % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, seconds)
        } else {
            return String(format: "%02d:%02d", minutes, seconds)
        }
    }
    
    var formattedSpeed: String {
        let kmh = currentSpeed * 3.6
        return String(format: "%.1f km/h", kmh)
    }
    
    var formattedPace: String {
        guard currentSpeed > 0.5 else { return "--'--\"" }
        let paceSeconds = 1000.0 / currentSpeed  // 每公里秒数
        let minutes = Int(paceSeconds) / 60
        let seconds = Int(paceSeconds) % 60
        return String(format: "%d'%02d\"", minutes, seconds)
    }
}

// MARK: - 轨迹数据（用于导出和上传）
struct TrackData {
    let points: [TrackPoint]
    let totalDistance: Double
    let elevationGain: Double
    let duration: Int
    let startedAt: Date
    let endedAt: Date
}

// MARK: - AMapLocationManagerDelegate
extension RouteRecordingService: AMapLocationManagerDelegate {
    func amapLocationManager(_ manager: AMapLocationManager!, didUpdate location: CLLocation!) {
        guard let location = location else { return }
        processLocation(location)
    }
    
    func amapLocationManager(_ manager: AMapLocationManager!, didFailWithError error: Error!) {
        print("❌ 记录定位失败: \(error?.localizedDescription ?? "未知")")
    }
    
    func amapLocationManager(_ manager: AMapLocationManager!, didChange status: CLAuthorizationStatus) {
        if status == .notDetermined {
            headingManager.requestWhenInUseAuthorization()
        }
    }
}

// MARK: - CLLocationManagerDelegate (heading)
extension RouteRecordingService: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {
        if status == .authorizedWhenInUse || status == .authorizedAlways {
            manager.startUpdatingHeading()
        }
    }
}

// MARK: - GPX 导出
extension TrackData {
    func toGPX() -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        
        var gpx = """
        <?xml version="1.0" encoding="UTF-8"?>
        <gpx version="1.1" creator="CityWalk"
          xmlns="http://www.topografix.com/GPX/1/1"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
          <metadata>
            <time>\(formatter.string(from: startedAt))</time>
          </metadata>
          <trk>
            <name>CityWalk Track</name>
            <trkseg>
        
        """
        
        for point in points {
            gpx += "      <trkpt lat=\"\(point.latitude)\" lon=\"\(point.longitude)\">\n"
            if let alt = point.altitude {
                gpx += "        <ele>\(String(format: "%.1f", alt))</ele>\n"
            }
            gpx += "        <time>\(formatter.string(from: point.timestamp))</time>\n"
            if let speed = point.speed, speed >= 0 {
                gpx += "        <speed>\(String(format: "%.2f", speed))</speed>\n"
            }
            if let course = point.course, course >= 0 {
                gpx += "        <course>\(String(format: "%.1f", course))</course>\n"
            }
            gpx += "      </trkpt>\n"
        }
        
        gpx += """
            </trkseg>
          </trk>
        </gpx>
        
        """
        
        return gpx
    }
    
    /// 保存 GPX 到本地 Documents 目录
    func saveGPXLocally(name: String? = nil) -> URL? {
        let fileName = name ?? "CityWalk_\(Int(startedAt.timeIntervalSince1970))"
        let gpxContent = toGPX()
        
        let documentsDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let gpxDir = documentsDir.appendingPathComponent("GPX", isDirectory: true)
        
        try? FileManager.default.createDirectory(at: gpxDir, withIntermediateDirectories: true)
        
        let fileURL = gpxDir.appendingPathComponent("\(fileName).gpx")
        do {
            try gpxContent.write(to: fileURL, atomically: true, encoding: .utf8)
            print("✅ GPX 已保存: \(fileURL.path)")
            return fileURL
        } catch {
            print("❌ GPX 保存失败: \(error)")
            return nil
        }
    }
    
    /// 转换为后端 RouteCreate 请求格式
    func toRouteCreateRequest(name: String, description: String? = nil, difficulty: String = "medium", tags: [String] = [], isPublished: Bool = true) -> [String: Any] {
        let pointsData = points.map { point -> [String: Any] in
            var pt: [String: Any] = [
                "location": [
                    "type": "Point",
                    "coordinates": [point.longitude, point.latitude]
                ],
                "is_waypoint": false
            ]
            if let alt = point.altitude {
                pt["elevation"] = alt
            }
            return pt
        }
        
        guard let first = points.first, let last = points.last else {
            return [:]
        }
        
        var body: [String: Any] = [
            "name": name,
            "points": pointsData,
            "distance": totalDistance,
            "elevation_gain": elevationGain,
            "estimated_duration": duration,
            "start_location": [
                "longitude": first.longitude,
                "latitude": first.latitude
            ],
            "end_location": [
                "longitude": last.longitude,
                "latitude": last.latitude
            ],
            "difficulty": difficulty,
            "tags": tags,
            "is_published": isPublished
        ]
        
        if let desc = description {
            body["description"] = desc
        }
        
        return body
    }
}

// MARK: - 上传服务
extension APIService {
    /// 上传路线到远端
    func uploadRoute(trackData: TrackData, name: String, description: String? = nil, difficulty: String = "medium", tags: [String] = [], isPublished: Bool = true) async throws -> Route {
        let url = URL(string: "\(AppConfig.apiBaseURL)/routes")!
        
        let body = trackData.toRouteCreateRequest(
            name: name,
            description: description,
            difficulty: difficulty,
            tags: tags,
            isPublished: isPublished
        )
        
        let bodyData = try? JSONSerialization.data(withJSONObject: body)
        var request = try authenticatedRequest(for: url, method: "POST", body: bodyData)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 || httpResponse.statusCode == 201 else {
            let statusCode = (response as? HTTPURLResponse)?.statusCode ?? 0
            let responseBody = String(data: data, encoding: .utf8) ?? ""
            print("❌ 上传路线失败: status=\(statusCode), body=\(responseBody)")
            throw APIError.invalidResponse
        }
        
        // 返回格式: {"code": 0, "message": "ok", "data": {...}}
        let apiResponse = try decodeResponse(Route.self, from: data)
        guard apiResponse.code == 0, let route = apiResponse.data else {
            throw APIError.networkError(apiResponse.message)
        }
        return route
    }
}
