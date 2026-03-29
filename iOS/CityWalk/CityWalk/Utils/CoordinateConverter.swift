import CoreLocation

/// 坐标转换工具（WGS-84 转 GCJ-02 火星坐标）
class CoordinateConverter {
    
    // 中国境内边界
    private static let chinaBounds = (
        minLat: 0.8293,
        maxLat: 55.8271,
        minLon: 72.004,
        maxLon: 137.8347
    )
    
    // 偏移参数
    private static let a = 6378245.0
    private static let ee = 0.00669342162296594323
    
    /// 判断是否在中国境内
    static func isInChina(_ coordinate: CLLocationCoordinate2D) -> Bool {
        return coordinate.latitude > chinaBounds.minLat &&
               coordinate.latitude < chinaBounds.maxLat &&
               coordinate.longitude > chinaBounds.minLon &&
               coordinate.longitude < chinaBounds.maxLon
    }
    
    /// WGS-84 转 GCJ-02
    static func wgs84ToGcj02(_ coordinate: CLLocationCoordinate2D) -> CLLocationCoordinate2D {
        if !isInChina(coordinate) {
            return coordinate
        }
        
        let lat = coordinate.latitude
        let lon = coordinate.longitude
        
        let dLat = transformLat(lon - 105.0, lat - 35.0)
        let dLon = transformLon(lon - 105.0, lat - 35.0)
        
        let radLat = lat / 180.0 * .pi
        var magic = sin(radLat)
        magic = 1 - ee * magic * magic
        let sqrtMagic = sqrt(magic)
        
        let latOffset = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * .pi)
        let lonOffset = (dLon * 180.0) / (a / sqrtMagic * cos(radLat) * .pi)
        
        return CLLocationCoordinate2D(
            latitude: lat + latOffset,
            longitude: lon + lonOffset
        )
    }
    
    /// 批量转换坐标
    static func wgs84ToGcj02(_ coordinates: [CLLocationCoordinate2D]) -> [CLLocationCoordinate2D] {
        return coordinates.map { wgs84ToGcj02($0) }
    }
    
    // 转换纬度偏移
    private static func transformLat(_ lon: Double, _ lat: Double) -> Double {
        var ret = -100.0 + 2.0 * lon + 3.0 * lat + 0.2 * lat * lat + 0.1 * lon * lat + 0.2 * sqrt(abs(lon))
        ret += (20.0 * sin(6.0 * lon * .pi) + 20.0 * sin(2.0 * lon * .pi)) * 2.0 / 3.0
        ret += (20.0 * sin(lat * .pi) + 40.0 * sin(lat / 3.0 * .pi)) * 2.0 / 3.0
        ret += (160.0 * sin(lat / 12.0 * .pi) + 320 * sin(lat * .pi / 30.0)) * 2.0 / 3.0
        return ret
    }
    
    // 转换经度偏移
    private static func transformLon(_ lon: Double, _ lat: Double) -> Double {
        var ret = 300.0 + lon + 2.0 * lat + 0.1 * lon * lon + 0.1 * lon * lat + 0.1 * sqrt(abs(lon))
        ret += (20.0 * sin(6.0 * lon * .pi) + 20.0 * sin(2.0 * lon * .pi)) * 2.0 / 3.0
        ret += (20.0 * sin(lon * .pi) + 40.0 * sin(lon / 3.0 * .pi)) * 2.0 / 3.0
        ret += (150.0 * sin(lon / 12.0 * .pi) + 300.0 * sin(lon / 30.0 * .pi)) * 2.0 / 3.0
        return ret
    }
}
