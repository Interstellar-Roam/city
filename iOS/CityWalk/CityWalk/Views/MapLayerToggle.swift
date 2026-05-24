import SwiftUI

// MARK: - 地图图层切换按钮

enum MapLayerMode: String, CaseIterable, Identifiable {
    case standard = "标准地图"
    case contour = "等高线叠加"
    
    var id: String { rawValue }
    
    var icon: String {
        switch self {
        case .standard: return "map"
        case .contour:  return "map.circle"
        }
    }
}

struct MapLayerToggle: View {
    @Binding var selectedLayer: MapLayerMode
    
    var body: some View {
        Menu {
            ForEach(MapLayerMode.allCases) { layer in
                Button {
                    selectedLayer = layer
                } label: {
                    HStack {
                        Image(systemName: layer == selectedLayer ? "checkmark" : layer.icon)
                            .foregroundColor(layer == selectedLayer ? .accentColor : .primary)
                        Text(layer.rawValue)
                    }
                }
            }
        } label: {
            Image(systemName: "map")
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(.primary)
                .frame(width: 36, height: 36)
                .background(.regularMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .shadow(color: .black.opacity(0.1), radius: 2, y: 1)
        }
    }
}
