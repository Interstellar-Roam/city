import Foundation
import MAMapKit

// MARK: - 等高线瓦片叠加层

/// OpenTopoMap 等高线/路网瓦片叠加层。
/// tile.opencyclemap.org 国内不可用，改用 OpenTopoMap（免费、含等高线）。
final class OCMTileOverlay: MATileOverlay {
    
    static func create() -> OCMTileOverlay {
        // tile.opencyclemap.org 国内被屏蔽，使用 OpenTopoMap（同样含等高线）
        let overlay = OCMTileOverlay(urlTemplate: "https://tile.opentopomap.org/{z}/{x}/{y}.png")!
        overlay.tileSize = CGSize(width: 256, height: 256)
        overlay.minimumZ = 0
        overlay.maximumZ = 17
        return overlay
    }
}
