import SwiftUI
import MapKit
import Photos

// MARK: - 路线分享卡片
struct ShareCardView: View {
    let route: Route
    @State private var isSaving = false
    @State private var showToast = false
    @State private var mapImage: UIImage?
    @Environment(\.dismiss) private var dismiss

    private let cardWidth: CGFloat = 300
    private let mapHeight: CGFloat = 240
    private let infoHeight: CGFloat = 140

    // 解析坐标
    private var clCoordinates: [CLLocationCoordinate2D] {
        route.points?.compactMap { p in
            let coords = p.location.coordinates
            guard coords.count == 2 else { return nil }
            return CLLocationCoordinate2D(latitude: coords[1], longitude: coords[0])
        } ?? []
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
            .overlay(Group {
                if showToast { toastView.transition(.move(edge: .bottom).combined(with: .opacity)) }
            }, alignment: .bottom)
            .animation(.easeInOut, value: showToast)
            .task { await generateMapSnapshot() }
        }
    }

    // MARK: - 卡片
    private var cardView: some View {
        VStack(spacing: 0) {
            // 地图区域
            mapSection.frame(width: cardWidth, height: mapHeight)
            // 信息区域
            infoSection.frame(width: cardWidth, height: infoHeight)
        }
        .frame(width: cardWidth, height: mapHeight + infoHeight)
    }

    // MARK: - 地图
    private var mapSection: some View {
        ZStack(alignment: .bottomLeading) {
            if let img = mapImage {
                Image(uiImage: img)
                    .resizable().scaledToFill()
                    .frame(width: cardWidth, height: mapHeight).clipped()
            } else {
                Rectangle().fill(Color(.systemGray5))
                    .overlay(ProgressView().tint(.orange))
            }

            // 底部渐变遮罩
            LinearGradient(colors: [.clear, .black.opacity(0.5)], startPoint: .top, endPoint: .bottom)
                .frame(height: 60)

            // 图例
            HStack(spacing: 12) {
                Label("起", systemImage: "circle.fill").font(.caption2).foregroundColor(.green)
                Label("终", systemImage: "circle.fill").font(.caption2).foregroundColor(.red)
                if let coords = route.points, !coords.isEmpty {
                    Text("\(coords.count)点").font(.caption2).foregroundColor(.white.opacity(0.7))
                }
            }
            .padding(.horizontal, 12).padding(.vertical, 6)
            .background(Color.black.opacity(0.4)).cornerRadius(8)
            .padding(12)
        }
        .frame(width: cardWidth, height: mapHeight).clipped()
    }

    // MARK: - 路线信息
    private var infoSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(route.name)
                .font(.system(size: 18, weight: .bold, design: .rounded))
                .lineLimit(1).padding(.top, 14)

            HStack(spacing: 16) {
                statBlock(icon: "point.topleft.down.to.point.bottomright.curvepath", value: route.formattedDistance, label: "距离")
                if let d = route.duration {
                    statBlock(icon: "clock", value: route.formattedDuration, label: "时长")
                }
                if let g = route.elevationGain {
                    statBlock(icon: "mountain.2.fill", value: String(format: "%.0fm", g), label: "爬升")
                }
            }.padding(.top, 10)

            Spacer()

            HStack {
                if let diff = route.difficulty {
                    Label(diff.displayText, systemImage: diff.icon).font(.caption2)
                        .foregroundColor(diff.color == "green" ? .green : diff.color == "orange" ? .orange : .red)
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .background(Color(.systemGray6)).cornerRadius(6)
                }
                Spacer()
                HStack(spacing: 4) {
                    Image(systemName: "figure.walk.circle.fill").font(.caption2)
                    Text("CityWalk").font(.caption2.bold())
                }.foregroundColor(.secondary)
            }.padding(.bottom, 12)
        }
        .padding(.horizontal, 20)
        .background(Color(.systemBackground))
    }

    private func statBlock(icon: String, value: String, label: String) -> some View {
        VStack(spacing: 2) {
            HStack(spacing: 4) {
                Image(systemName: icon).font(.caption2).foregroundColor(.orange)
                Text(value).font(.system(size: 13, weight: .medium, design: .rounded))
            }
            Text(label).font(.caption2).foregroundColor(.secondary)
        }
    }

    // MARK: - 生成地图快照
    private func generateMapSnapshot() async {
        let coords = clCoordinates
        guard coords.count >= 2 else { return }

        let lats = coords.map(\.latitude)
        let lons = coords.map(\.longitude)
        guard let minLat = lats.min(), let maxLat = lats.max(),
              let minLon = lons.min(), let maxLon = lons.max() else { return }

        let center = CLLocationCoordinate2D(
            latitude: (minLat + maxLat) / 2,
            longitude: (minLon + maxLon) / 2
        )
        let span = MKCoordinateSpan(
            latitudeDelta: maxLat - minLat + 0.008,
            longitudeDelta: maxLon - minLon + 0.008
        )

        let options = MKMapSnapshotter.Options()
        options.region = MKCoordinateRegion(center: center, span: span)
        options.size = CGSize(width: cardWidth * 3, height: mapHeight * 3)
        options.scale = UIScreen.main.scale
        options.mapType = .standard

        let snapshotter = MKMapSnapshotter(options: options)
        do {
            let snapshot = try await snapshotter.start()
            mapImage = await drawRoute(on: snapshot.image, snapshot: snapshot, coords: coords)
        } catch {
            print("Map snapshot failed: \(error)")
        }
    }

    // 在地图上绘制路线
    private func drawRoute(on image: UIImage, snapshot: MKMapSnapshotter.Snapshot, coords: [CLLocationCoordinate2D]) -> UIImage {
        let renderer = UIGraphicsImageRenderer(size: image.size, format: image.imageRendererFormat)
        return renderer.image { ctx in
            image.draw(at: .zero)

            let points = coords.map { snapshot.point(for: $0) }
            guard points.count >= 2 else { return }

            // 外发光
            let glowPath = UIBezierPath()
            glowPath.move(to: points[0])
            for pt in points.dropFirst() { glowPath.addLine(to: pt) }
            glowPath.lineWidth = 8
            glowPath.lineCapStyle = .round
            glowPath.lineJoinStyle = .round
            UIColor.orange.withAlphaComponent(0.25).setStroke()
            glowPath.stroke()

            // 主线
            let path = UIBezierPath()
            path.move(to: points[0])
            for pt in points.dropFirst() { path.addLine(to: pt) }
            path.lineWidth = 5
            path.lineCapStyle = .round
            path.lineJoinStyle = .round
            UIColor.systemOrange.setStroke()
            path.stroke()

            // 起点标记
            let startPt = points[0]
            let startCircle = UIBezierPath(ovalIn: CGRect(x: startPt.x - 7, y: startPt.y - 7, width: 14, height: 14))
            UIColor.white.setFill()
            startCircle.fill()
            let startInner = UIBezierPath(ovalIn: CGRect(x: startPt.x - 4, y: startPt.y - 4, width: 8, height: 8))
            UIColor.systemGreen.setFill()
            startInner.fill()

            // 终点标记
            if let endPt = points.last {
                let endCircle = UIBezierPath(ovalIn: CGRect(x: endPt.x - 7, y: endPt.y - 7, width: 14, height: 14))
                UIColor.white.setFill()
                endCircle.fill()
                let endInner = UIBezierPath(ovalIn: CGRect(x: endPt.x - 4, y: endPt.y - 4, width: 8, height: 8))
                UIColor.systemRed.setFill()
                endInner.fill()
            }
        }
    }

    // MARK: - Toast
    private var toastView: some View {
        HStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill").foregroundColor(.green)
            Text("已保存到相册").font(.subheadline).foregroundColor(.white)
        }
        .padding(.horizontal, 20).padding(.vertical, 12)
        .background(Capsule().fill(Color.black.opacity(0.8))).padding(.bottom, 40)
    }

    // MARK: - 保存
    private func saveToPhotos() {
        isSaving = true
        let renderer = ImageRenderer(content: cardView)
        renderer.scale = UIScreen.main.scale
        if let image = renderer.uiImage {
            PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            } completionHandler: { success, _ in
                DispatchQueue.main.async {
                    isSaving = false
                    if success { showToast = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { showToast = false; dismiss() }
                    }
                }
            }
        } else { isSaving = false }
    }
}
