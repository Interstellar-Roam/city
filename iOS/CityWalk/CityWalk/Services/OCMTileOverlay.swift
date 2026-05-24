import Foundation
import MAMapKit

// MARK: - OCM 瓦片叠加层

/// 从 OpenCycleMap 加载等高线和路网瓦片，
/// 自动处理 GCJ-02（高德）→ WGS-84（OCM）的坐标转换。
final class OCMTileOverlay: MATileOverlay {
    
    override init() {
        // 先用一个占位 URL（实际通过 loadTile 动态构建）
        super.init(urlTemplate: "local://{z}/{x}/{y}")
        self.tileSize = CGSize(width: 256, height: 256)
        self.minimumZ = 0
        self.maximumZ = 18
    }
    
    // MARK: - 瓦片加载
    
    override func loadTile(at path: MATileOverlayPath, result: @escaping (Data?, Error?) -> Void) {
        // zoom 范围保护
        guard path.z >= 0 && path.z <= 18 else {
            result(nil, nil)
            return
        }
        
        // 1. 高德瓦片索引 → GCJ-02 经纬度
        let (lngGcj, latGcj) = CoordTransform.tileToLngLat(
            x: path.x, y: path.y, zoom: path.z
        )
        
        // 2. GCJ-02 → WGS-84
        let (lngWgs, latWgs) = CoordTransform.gcj02ToWgs84(
            lng: lngGcj, lat: latGcj
        )
        
        // 3. WGS-84 经纬度 → OCM 瓦片索引
        let (xWgs, yWgs) = CoordTransform.lngLatToTile(
            lng: lngWgs, lat: latWgs, zoom: path.z
        )
        
        // 4. 构建 OCM 瓦片 URL
        let urlString = "https://tile.opencyclemap.org/cycle/\(path.z)/\(xWgs)/\(yWgs).png"
        guard let url = URL(string: urlString) else {
            result(nil, nil)
            return
        }
        
        // 5. 下载瓦片
        let task = URLSession.shared.dataTask(with: url) { data, _, error in
            if let error = error {
                // 网络错误静默处理，瓦片区域透明
                result(nil, nil)
                return
            }
            result(data, nil)
        }
        task.resume()
    }
}
