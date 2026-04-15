import Foundation
import AMapFoundationKit
import AMapLocationKit
import CoreLocation
import AVFoundation

// MARK: - 高德地图导航服务
class AMapNavigationService: NSObject, ObservableObject {
    private let locationManager = AMapLocationManager()
    private let speechSynthesizer = AVSpeechSynthesizer()
    
    let route: Route
    let mode: NavigationMode
    let enableVoice: Bool
    let powerSavingMode: Bool
    
    var routeCoordinates: [CLLocationCoordinate2D] = []
    private var totalDistance: Double = 0
    var currentSegmentIndex: Int = 0
    private var startTime: Date?
    private var lastLocation: CLLocation?
    private var hasAnnouncedArrival = false
    private var lastOffRouteAnnounceTime: Date?
    
    @Published var currentLocation: CLLocationCoordinate2D?
    @Published var currentHeading: Double = 0
    @Published var nextTurn: TurnInstruction?
    @Published var remainingDistanceText: String = "0 公里"
    @Published var estimatedTimeText: String = "0 分钟"
    @Published var currentSpeedText: String = "0 km/h"
    @Published var isPaused: Bool = false
    @Published var isOffRoute: Bool = false
    @Published var navigationProgress: Double = 0.0
    @Published var showArrivalAlert = false
    
    struct TurnInstruction {
        let distance: Double
        let direction: String
        let roadName: String?
        let icon: String
    }
    
    init(route: Route, mode: NavigationMode, enableVoice: Bool, powerSavingMode: Bool) {
        self.route = route
        self.mode = mode
        self.enableVoice = enableVoice
        self.powerSavingMode = powerSavingMode
        
        super.init()
        
        // 准备路线数据
        if let points = route.points {
            self.routeCoordinates = CoordinateConverter.wgs84ToGcj02(points.map { $0.location.coordinate })
            self.totalDistance = calculateTotalDistance()
        }
        
        setupLocationManager()
        
        // 初始化显示数据
        self.remainingDistanceText = route.formattedDistance
        self.estimatedTimeText = route.formattedDuration
    }
    
    private func setupLocationManager() {
        locationManager.delegate = self
        
        // 设置定位精度
        if powerSavingMode {
            locationManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        } else {
            locationManager.desiredAccuracy = kCLLocationAccuracyBestForNavigation
        }
    }
    
    func startNavigation() {
        // 开始连续定位
        locationManager.startUpdatingLocation()
        
        startTime = Date()
        
        if enableVoice {
            speak("导航开始，请沿路线前行")
        }
    }
    
    func stopNavigation() {
        locationManager.stopUpdatingLocation()
    }
    
    func togglePause() {
        isPaused.toggle()
        
        if isPaused {
            locationManager.stopUpdatingLocation()
            speak("导航已暂停")
        } else {
            locationManager.startUpdatingLocation()
            speak("继续导航")
        }
    }
    
    private func calculateTotalDistance() -> Double {
        var distance: Double = 0
        for i in 1..<routeCoordinates.count {
            distance += distanceBetween(routeCoordinates[i-1], routeCoordinates[i])
        }
        return distance
    }
    
    private func distanceBetween(_ from: CLLocationCoordinate2D, _ to: CLLocationCoordinate2D) -> Double {
        let loc1 = CLLocation(latitude: from.latitude, longitude: from.longitude)
        let loc2 = CLLocation(latitude: to.latitude, longitude: to.longitude)
        return loc1.distance(from: loc2)
    }
    
    private func speak(_ text: String) {
        guard enableVoice else { return }
        
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "zh-CN")
        utterance.rate = 0.5
        speechSynthesizer.speak(utterance)
    }
    
    private func updateNavigationData(location: CLLocation) {
        guard !routeCoordinates.isEmpty, totalDistance > 0 else { return }
        
        // 1. 找到路线上最近的点
        var minDistance = Double.infinity
        var nearestIndex = 0
        
        for (index, coord) in routeCoordinates.enumerated() {
            let routeLoc = CLLocation(latitude: coord.latitude, longitude: coord.longitude)
            let distance = location.distance(from: routeLoc)
            
            if distance < minDistance {
                minDistance = distance
                nearestIndex = index
            }
        }
        
        // 2. 检测是否偏离路线
        isOffRoute = minDistance > 50
        
        if isOffRoute {
            let now = Date()
            if lastOffRouteAnnounceTime == nil || now.timeIntervalSince(lastOffRouteAnnounceTime!) > 30 {
                lastOffRouteAnnounceTime = now
                speak("您已偏离路线，请返回")
            }
        }
        
        // 3. 更新当前路段索引
        currentSegmentIndex = nearestIndex
        
        // 4. 计算剩余距离
        var remainingDistance: Double = 0
        if nearestIndex < routeCoordinates.count - 1 {
            let nearestCoord = routeCoordinates[nearestIndex]
            remainingDistance += distanceBetween(location.coordinate, nearestCoord)
            
            for i in (nearestIndex + 1)..<routeCoordinates.count {
                remainingDistance += distanceBetween(routeCoordinates[i-1], routeCoordinates[i])
            }
        }
        
        // 5. 更新进度
        navigationProgress = min(1.0, max(0, 1.0 - remainingDistance / totalDistance))
        
        // 6. 更新显示文本
        if remainingDistance < 1000 {
            remainingDistanceText = String(format: "%.0f 米", remainingDistance)
        } else {
            remainingDistanceText = String(format: "%.1f 公里", remainingDistance / 1000)
        }
        
        // 7. 计算预计时间
        let speed: Double
        switch mode {
        case .walking: speed = 5.0 / 3.6
        case .running: speed = 10.0 / 3.6
        case .cycling: speed = 20.0 / 3.6
        }
        
        let remainingSeconds = remainingDistance / speed
        let minutes = Int(remainingSeconds / 60)
        let hours = minutes / 60
        let mins = minutes % 60
        
        if hours > 0 {
            estimatedTimeText = "\(hours)小时\(mins)分钟"
        } else {
            estimatedTimeText = "\(mins)分钟"
        }
        
        // 8. 更新速度
        let speedKmh = location.speed * 3.6
        if speedKmh >= 0 {
            currentSpeedText = String(format: "%.1f km/h", speedKmh)
        }
        
        // 9. 更新当前位置
        currentLocation = location.coordinate
        currentHeading = location.course
        
        // 10. 检测到达终点
        if remainingDistance < 20 && !hasAnnouncedArrival {
            hasAnnouncedArrival = true
            showArrivalAlert = true
            speak("您已到达目的地")
        }
        
        // 11. 生成转向提示
        updateTurnInstruction(nearestIndex: nearestIndex)
        
        lastLocation = location
    }
    
    private func updateTurnInstruction(nearestIndex: Int) {
        guard nearestIndex < routeCoordinates.count - 10 else {
            nextTurn = nil
            return
        }
        
        let currentDir = calculateBearing(
            from: routeCoordinates[nearestIndex],
            to: routeCoordinates[min(nearestIndex + 5, routeCoordinates.count - 1)]
        )
        
        for i in (nearestIndex + 10)..<min(nearestIndex + 50, routeCoordinates.count - 5) {
            let futureDir = calculateBearing(
                from: routeCoordinates[i],
                to: routeCoordinates[min(i + 5, routeCoordinates.count - 1)]
            )
            
            let angleDiff = abs(currentDir - futureDir)
            
            if angleDiff > 30 && angleDiff < 330 {
                let distance = distanceBetween(routeCoordinates[nearestIndex], routeCoordinates[i])
                
                let direction: String
                let icon: String
                
                if angleDiff < 150 {
                    direction = "右转"
                    icon = "arrow.turn.up.right"
                } else {
                    direction = "左转"
                    icon = "arrow.turn.up.left"
                }
                
                nextTurn = TurnInstruction(
                    distance: distance,
                    direction: direction,
                    roadName: nil,
                    icon: icon
                )
                
                if distance < 50 && distance > 40 {
                    speak("前方\(Int(distance))米\(direction)")
                } else if distance < 10 {
                    speak(direction)
                }
                
                return
            }
        }
        
        nextTurn = nil
    }
    
    private func calculateBearing(from: CLLocationCoordinate2D, to: CLLocationCoordinate2D) -> Double {
        let lat1 = from.latitude * .pi / 180
        let lon1 = from.longitude * .pi / 180
        let lat2 = to.latitude * .pi / 180
        let lon2 = to.longitude * .pi / 180
        
        let dLon = lon2 - lon1
        
        let y = sin(dLon) * cos(lat2)
        let x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dLon)
        
        let bearing = atan2(y, x) * 180 / .pi
        
        return (bearing + 360).truncatingRemainder(dividingBy: 360)
    }
    
    deinit {
        stopNavigation()
    }
}

// MARK: - AMapLocationManagerDelegate
extension AMapNavigationService: AMapLocationManagerDelegate {
    func amapLocationManager(_ manager: AMapLocationManager!, didUpdateLocation location: CLLocation!) {
        guard !isPaused, let location = location else { return }
        
        DispatchQueue.main.async {
            self.updateNavigationData(location: location)
        }
    }
    
    func amapLocationManager(_ manager: AMapLocationManager!, didFailWithError error: Error!) {
        print("❌ 高德定位失败: \(error?.localizedDescription ?? "未知错误")")
    }
}
