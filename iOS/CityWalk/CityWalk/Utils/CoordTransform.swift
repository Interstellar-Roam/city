import Foundation
import CoreLocation

// MARK: - GCJ-02 与 WGS-84 坐标转换工具

enum CoordTransform {
    
    // MARK: - 常量
    
    private static let a = 6378245.0          // 长半轴
    private static let ee = 0.00669342162296594323  // 偏心率平方
    
    // MARK: - GCJ-02 → WGS-84
    
    /// 将 GCJ-02 经纬度转换为 WGS-84（低精度，1次迭代）
    static func gcj02ToWgs84(lng: Double, lat: Double) -> (lng: Double, lat: Double) {
        // 排除境外坐标（无需转换）
        if isOutsideChina(lng: lng, lat: lat) {
            return (lng, lat)
        }
        
        let (dlng, dlat) = gcjOffset(lng: lng, lat: lat)
        return (lng - dlng, lat - dlat)
    }
    
    // MARK: - WGS-84 → GCJ-02
    
    /// 将 WGS-84 经纬度转换为 GCJ-02
    static func wgs84ToGcj02(lng: Double, lat: Double) -> (lng: Double, lat: Double) {
        if isOutsideChina(lng: lng, lat: lat) {
            return (lng, lat)
        }
        
        let (dlng, dlat) = gcjOffset(lng: lng, lat: lat)
        return (lng + dlng, lat + dlat)
    }
    
    // MARK: - 私有：偏移计算
    
    private static func gcjOffset(lng: Double, lat: Double) -> (dlng: Double, dlat: Double) {
        let radLat = lat / 180.0 * .pi
        var magic = sin(radLat)
        magic = 1.0 - ee * magic * magic
        let sqrtMagic = sqrt(magic)
        
        var dlat = transformLat(x: lng - 105.0, y: lat - 35.0)
        var dlng = transformLng(x: lng - 105.0, y: lat - 35.0)
        
        dlat = (dlat * 180.0) / ((a * (1.0 - ee)) / (magic * sqrtMagic) * .pi)
        dlng = (dlng * 180.0) / (a / sqrtMagic * cos(radLat) * .pi)
        
        return (dlng, dlat)
    }
    
    private static func transformLat(x: Double, y: Double) -> Double {
        var lat = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * sqrt(abs(x))
        lat += (20.0 * sin(6.0 * x * .pi) + 20.0 * sin(2.0 * x * .pi)) * 2.0 / 3.0
        lat += (20.0 * sin(y * .pi) + 40.0 * sin(y / 3.0 * .pi)) * 2.0 / 3.0
        lat += (160.0 * sin(y / 12.0 * .pi) + 320.0 * sin(y * .pi / 30.0)) * 2.0 / 3.0
        return lat
    }
    
    private static func transformLng(x: Double, y: Double) -> Double {
        var lng = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * sqrt(abs(x))
        lng += (20.0 * sin(6.0 * x * .pi) + 20.0 * sin(2.0 * x * .pi)) * 2.0 / 3.0
        lng += (20.0 * sin(x * .pi) + 40.0 * sin(x / 3.0 * .pi)) * 2.0 / 3.0
        lng += (150.0 * sin(x / 12.0 * .pi) + 300.0 * sin(x / 30.0 * .pi)) * 2.0 / 3.0
        return lng
    }
    
    // MARK: - 境外判断
    
    /// 判断坐标是否在中国境外（境外无需 GCJ-02 偏移）
    static func isOutsideChina(lng: Double, lat: Double) -> Bool {
        return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
    }
    
    // MARK: - 瓦片索引 ↔ 经纬度
    
    /// 经纬度 → 瓦片索引
    static func lngLatToTile(lng: Double, lat: Double, zoom: Int) -> (x: Int, y: Int) {
        let n = pow(2.0, Double(zoom))
        let x = Int(floor((lng + 180.0) / 360.0 * n))
        let latRad = lat * .pi / 180.0
        let y = Int(floor((1.0 - log(tan(latRad) + 1.0 / cos(latRad)) / .pi) / 2.0 * n))
        return (x, y)
    }
    
    /// 瓦片索引 → 左上角经纬度
    static func tileToLngLat(x: Int, y: Int, zoom: Int) -> (lng: Double, lat: Double) {
        let n = pow(2.0, Double(zoom))
        let lng = Double(x) / n * 360.0 - 180.0
        let lat = atan(sinh(.pi * (1.0 - 2.0 * Double(y) / n))) * 180.0 / .pi
        return (lng, lat)
    }
}
