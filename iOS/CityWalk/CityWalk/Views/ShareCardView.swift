import SwiftUI
import Photos

// MARK: - 路线分享卡片
struct ShareCardView: View {
    let route: Route
    @State private var isSaving = false
    @State private var showToast = false
    @Environment(\.dismiss) private var dismiss

    private let cardWidth: CGFloat = 300
    private let mapHeight: CGFloat = 220
    private let infoHeight: CGFloat = 150

    // 从 route.points 提取坐标
    private var coordinates: [(x: Double, y: Double)] {
        guard let points = route.points, points.count >= 2 else { return [] }
        let lons = points.map { $0.location.coordinates[0] }
        let lats = points.map { $0.location.coordinates[1] }
        guard let minLon = lons.min(), let maxLon = lons.max(),
              let minLat = lats.min(), let maxLat = lats.max() else { return [] }
        let rangeLon = max(maxLon - minLon, 0.001)
        let rangeLat = max(maxLat - minLat, 0.001)
        let padding: Double = 0.12
        let scaleX = (1.0 - padding * 2) / rangeLon
        let scaleY = (1.0 - padding * 2) / rangeLat
        return points.map {
            ((($0.location.coordinates[0] - minLon) * scaleX + padding),
             (($0.location.coordinates[1] - minLat) * scaleY + padding))
        }
    }

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                cardView
                    .cornerRadius(20)
                    .shadow(color: .black.opacity(0.15), radius: 10, y: 4)

                Button(action: saveToPhotos) {
                    HStack(spacing: 8) {
                        if isSaving { ProgressView().tint(.white) }
                        else { Image(systemName: "square.and.arrow.down.fill") }
                        Text(isSaving ? "保存中..." : "保存到相册")
                    }
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 32).padding(.vertical, 14)
                    .background(RoundedRectangle(cornerRadius: 16).fill(Color.orange))
                }
                .disabled(isSaving)
            }
            .navigationTitle("分享路线")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("关闭") { dismiss() } }
            }
            .overlay(
                Group {
                    if showToast {
                        toastView.transition(.move(edge: .bottom).combined(with: .opacity))
                    }
                }, alignment: .bottom
            )
            .animation(.easeInOut, value: showToast)
        }
    }

    // MARK: - 卡片
    private var cardView: some View {
        VStack(spacing: 0) {
            // 地图轨迹区
            routeMapSection
                .frame(width: cardWidth, height: mapHeight)

            // 路线信息区
            infoSection
                .frame(width: cardWidth, height: infoHeight)
        }
        .frame(width: cardWidth, height: mapHeight + infoHeight)
    }

    // MARK: - 地图轨迹
    private var routeMapSection: some View {
        ZStack(alignment: .bottomLeading) {
            // 深色背景
            Rectangle()
                .fill(Color(red: 0.12, green: 0.12, blue: 0.18))

            // 路线折线
            if coordinates.count >= 2 {
                Path { path in
                    let w = cardWidth
                    let h = mapHeight
                    for (i, coord) in coordinates.enumerated() {
                        let pt = CGPoint(x: coord.x * w, y: (1 - coord.y) * h)
                        if i == 0 { path.move(to: pt) }
                        else { path.addLine(to: pt) }
                    }
                }
                .stroke(
                    LinearGradient(colors: [.orange, .pink], startPoint: .leading, endPoint: .trailing),
                    style: StrokeStyle(lineWidth: 3, lineCap: .round, lineJoin: .round)
                )
                .shadow(color: .orange.opacity(0.5), radius: 4)

                // 外发光
                Path { path in
                    let w = cardWidth
                    let h = mapHeight
                    for (i, coord) in coordinates.enumerated() {
                        let pt = CGPoint(x: coord.x * w, y: (1 - coord.y) * h)
                        if i == 0 { path.move(to: pt) }
                        else { path.addLine(to: pt) }
                    }
                }
                .stroke(
                    Color.orange.opacity(0.2),
                    style: StrokeStyle(lineWidth: 8, lineCap: .round, lineJoin: .round)
                )

                // 起点
                let start = CGPoint(x: coordinates[0].x * cardWidth, y: (1 - coordinates[0].y) * mapHeight)
                Circle()
                    .fill(.green)
                    .frame(width: 10, height: 10)
                    .overlay(Circle().stroke(.white, lineWidth: 2))
                    .position(start)

                // 终点
                let end = CGPoint(x: coordinates.last!.x * cardWidth, y: (1 - coordinates.last!.y) * mapHeight)
                Circle()
                    .fill(.red)
                    .frame(width: 10, height: 10)
                    .overlay(Circle().stroke(.white, lineWidth: 2))
                    .position(end)
            }

            // 图例
            HStack(spacing: 16) {
                Label("起点", systemImage: "circle.fill")
                    .font(.caption2).foregroundColor(.green)
                Label("终点", systemImage: "circle.fill")
                    .font(.caption2).foregroundColor(.red)
            }
            .padding(12)
            .background(Color.black.opacity(0.4))
            .cornerRadius(8)
            .padding(12)
        }
        .clipped()
    }

    // MARK: - 路线信息
    private var infoSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            // 路线名
            Text(route.name)
                .font(.system(size: 18, weight: .bold, design: .rounded))
                .lineLimit(1)
                .padding(.top, 16)

            // 统计
            HStack(spacing: 16) {
                statItem(icon: "point.topleft.down.to.point.bottomright.curvepath", value: route.formattedDistance, label: "距离")
                if let duration = route.duration {
                    statItem(icon: "clock", value: route.formattedDuration, label: "时长")
                }
                if let gain = route.elevationGain {
                    statItem(icon: "mountain.2.fill", value: String(format: "%.0fm", gain), label: "爬升")
                }
            }
            .padding(.top, 12)

            Spacer()

            // 难度 + 标签 + Watermark
            HStack {
                if let diff = route.difficulty {
                    HStack(spacing: 4) {
                        Image(systemName: diff.icon).font(.caption)
                        Text(diff.displayText).font(.caption2)
                    }
                    .foregroundColor(diff.color == "green" ? .green : diff.color == "orange" ? .orange : .red)
                    .padding(.horizontal, 8).padding(.vertical, 4)
                    .background(Color(.systemGray6))
                    .cornerRadius(6)
                }
                if let tags = route.tags, let first = tags.first {
                    Text(first).font(.caption2).foregroundColor(.orange)
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .background(Color.orange.opacity(0.1)).cornerRadius(6)
                }
                Spacer()
                HStack(spacing: 4) {
                    Image(systemName: "figure.walk.circle.fill").font(.caption2)
                    Text("CityWalk").font(.caption2.bold())
                }
                .foregroundColor(.secondary)
            }
            .padding(.bottom, 14)
        }
        .padding(.horizontal, 20)
        .background(Color(.systemBackground))
    }

    private func statItem(icon: String, value: String, label: String) -> some View {
        VStack(spacing: 2) {
            HStack(spacing: 4) {
                Image(systemName: icon).font(.caption2).foregroundColor(.orange)
                Text(value).font(.system(size: 14, weight: .medium, design: .rounded))
            }
            Text(label).font(.caption2).foregroundColor(.secondary)
        }
    }

    // MARK: - Toast
    private var toastView: some View {
        HStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill").foregroundColor(.green)
            Text("已保存到相册").font(.subheadline).foregroundColor(.white)
        }
        .padding(.horizontal, 20).padding(.vertical, 12)
        .background(Capsule().fill(Color.black.opacity(0.8)))
        .padding(.bottom, 40)
    }

    // MARK: - 保存
    private func saveToPhotos() {
        isSaving = true
        let renderer = ImageRenderer(content: cardView)
        renderer.scale = UIScreen.main.scale
        if let image = renderer.uiImage {
            PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            } completionHandler: { success, error in
                DispatchQueue.main.async {
                    isSaving = false
                    if success { showToast = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            showToast = false; dismiss()
                        }
                    }
                }
            }
        } else { isSaving = false }
    }
}
