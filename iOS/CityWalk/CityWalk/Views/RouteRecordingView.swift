import SwiftUI
import MapKit

// MARK: - 路线记录主界面
struct RouteRecordingView: View {
    @StateObject private var recordingService = RouteRecordingService()
    @State private var showSaveSheet = false
    @State private var showMapPreview = false
    @State private var routeName = ""
    @State private var routeDescription = ""
    @State private var routeDifficulty = "medium"
    @State private var routeTags: [String] = []
    @State private var isUploading = false
    @State private var uploadSuccess = false
    @State private var errorMessage: String?
    @State private var isPublished = true
    
    private let difficulties = [("简单", "easy"), ("中等", "medium"), ("困难", "hard")]
    private let availableTags = ["徒步", "跑步", "骑行", "公园", "海边", "越野跑", "城市", "山地"]
    
    var body: some View {
        NavigationStack {
            ZStack {
                // 地图背景
                if recordingService.isRecording {
                    RecordingMapView(trackPoints: recordingService.trackPoints)
                        .ignoresSafeArea()
                        .opacity(showMapPreview ? 1 : 0)
                    
                    Color.black.opacity(showMapPreview ? 0.3 : 0)
                        .ignoresSafeArea()
                        .onTapGesture {
                            withAnimation { showMapPreview = false }
                        }
                }
                
                VStack(spacing: 0) {
                    if recordingService.isRecording {
                        recordingHeaderView
                    }
                    
                    Spacer()
                    
                    if !recordingService.isRecording {
                        // 未开始：展示开始按钮
                        startView
                    } else {
                        // 记录中：展示数据面板
                        recordingPanelView
                    }
                }
            }
            .navigationTitle(recordingService.isRecording ? "" : "新建路线")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if recordingService.isRecording {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            withAnimation { showMapPreview.toggle() }
                        } label: {
                            Image(systemName: showMapPreview ? "eye.slash" : "map")
                        }
                    }
                }
            }
            .sheet(isPresented: $showSaveSheet) {
                saveSheetView
            }
            .alert("保存成功！", isPresented: $uploadSuccess) {
                Button("好的") {}
            } message: {
                Text("路线已保存并上传到云端")
            }
            .alert("错误", isPresented: .constant(errorMessage != nil)) {
                Button("确定") { errorMessage = nil }
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }
    
    // MARK: - 开始视图
    
    private var startView: some View {
        VStack(spacing: 32) {
            Image(systemName: "figure.walk")
                .font(.system(size: 64))
                .foregroundColor(.orange)
            
            VStack(spacing: 8) {
                Text("记录你的路线")
                    .font(.title2.bold())
                Text("开始记录后，GPS 将追踪你的轨迹")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            
            Button {
                recordingService.startRecording()
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "record.circle")
                        .font(.title3)
                    Text("开始记录")
                        .font(.headline)
                }
                .foregroundColor(.white)
                .padding(.horizontal, 40)
                .padding(.vertical, 16)
                .background(Color.red)
                .cornerRadius(30)
            }
        }
        .padding()
    }
    
    // MARK: - 记录中头部
    
    private var recordingHeaderView: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Circle()
                        .fill(recordingService.isPaused ? Color.orange : Color.red)
                        .frame(width: 8, height: 8)
                    Text(recordingService.isPaused ? "已暂停" : "记录中")
                        .font(.caption.bold())
                        .foregroundColor(.white)
                }
                Text(recordingService.formattedDuration)
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }
            Spacer()
            
            VStack(alignment: .trailing, spacing: 4) {
                Text(recordingService.formattedDistance)
                    .font(.system(size: 24, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                Text("\(recordingService.trackPoints.count) 个点")
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.7))
            }
        }
        .padding()
        .background(Color(red: 0.10, green: 0.16, blue: 0.25))
    }
    
    // MARK: - 记录面板
    
    private var recordingPanelView: some View {
        VStack(spacing: 16) {
            // 数据卡片
            HStack(spacing: 12) {
                DataCard(value: recordingService.formattedSpeed, label: "速度", icon: "speedometer")
                DataCard(value: recordingService.formattedPace, label: "配速", icon: "figure.walk")
                DataCard(value: String(format: "%.0f m", recordingService.elevationGain), label: "爬升", icon: "mountain.2.fill")
            }
            .padding(.horizontal)
            
            // 控制按钮
            HStack(spacing: 24) {
                // 暂停/继续
                Button {
                    if recordingService.isPaused {
                        recordingService.resumeRecording()
                    } else {
                        recordingService.pauseRecording()
                    }
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: recordingService.isPaused ? "play.circle.fill" : "pause.circle.fill")
                            .font(.system(size: 44))
                        Text(recordingService.isPaused ? "继续" : "暂停")
                            .font(.caption)
                    }
                    .foregroundColor(recordingService.isPaused ? .green : .orange)
                }
                
                // 停止并保存
                Button {
                    if let trackData = recordingService.stopRecording() {
                        // 自动生成路线名
                        let formatter = DateFormatter()
                        formatter.dateFormat = "yyyy-MM-dd HH:mm"
                        routeName = "路线 \(formatter.string(from: Date()))"
                        showSaveSheet = true
                    }
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: "stop.circle.fill")
                            .font(.system(size: 44))
                        Text("停止")
                            .font(.caption)
                    }
                    .foregroundColor(.red)
                }
            }
            .padding(.vertical, 8)
        }
        .padding()
        .background(.ultraThinMaterial)
    }
    
    // MARK: - 保存弹窗
    
    private var saveSheetView: some View {
        NavigationStack {
            Form {
                Section("路线信息") {
                    TextField("路线名称", text: $routeName)
                    TextField("描述（可选）", text: $routeDescription, axis: .vertical)
                        .lineLimit(2...4)
                }
                
                Section("难度") {
                    Picker("难度", selection: $routeDifficulty) {
                        ForEach(difficulties, id: \.1) { diff in
                            Text(diff.0).tag(diff.1)
                        }
                    }
                    .pickerStyle(.segmented)
                }
                
                Section("标签") {
                    FlowLayout(spacing: 8) {
                        ForEach(availableTags, id: \.self) { tag in
                            TagChip(tag: tag, isSelected: routeTags.contains(tag)) {
                                if routeTags.contains(tag) {
                                    routeTags.removeAll { $0 == tag }
                                } else {
                                    routeTags.append(tag)
                                }
                            }
                        }
                    }
                }

                Section {
                    Toggle(isOn: $isPublished) {
                        Label("公开路线", systemImage: isPublished ? "globe.asia.australia" : "lock")
                    }
                } footer: {
                    Text(isPublished ? "所有人可在发现页看到这条路线" : "仅自己可见，不会出现在发现和搜索中")
                }
            }
            .navigationTitle("保存路线")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") {
                        saveAndUpload()
                    }
                    .disabled(isUploading)
                }
            }
        }
    }
    
    // MARK: - 操作
    
    private func saveAndUpload() {
        guard !routeName.isEmpty else {
            errorMessage = "请输入路线名称"
            return
        }
        
        let trackData = TrackData(
            points: recordingService.trackPoints,
            totalDistance: recordingService.totalDistance,
            elevationGain: recordingService.elevationGain,
            duration: Int(recordingService.elapsedTime),
            startedAt: Date(),
            endedAt: Date()
        )
        
        // 先本地保存 GPX
        trackData.saveGPXLocally(name: routeName)
        
        isUploading = true
        Task {
            do {
                let _ = try await APIService.shared.uploadRoute(
                    trackData: trackData,
                    name: routeName,
                    description: routeDescription.isEmpty ? nil : routeDescription,
                    difficulty: routeDifficulty,
                    tags: routeTags,
                    isPublished: isPublished
                )
                isUploading = false
                uploadSuccess = true
                showSaveSheet = false
            } catch {
                isUploading = false
                errorMessage = "上传失败: \(error.localizedDescription)"
            }
        }
    }
}

// MARK: - 记录中地图
struct RecordingMapView: UIViewRepresentable {
    let trackPoints: [TrackPoint]
    
    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        mapView.showsUserLocation = true
        mapView.isPitchEnabled = false
        mapView.isRotateEnabled = true
        mapView.showsCompass = false
        mapView.showsScale = false
        mapView.mapType = .standard
        mapView.userTrackingMode = .followWithHeading
        return mapView
    }
    
    func updateUIView(_ mapView: MKMapView, context: Context) {
        mapView.removeOverlays(mapView.overlays)
        
        let coords = trackPoints.map { $0.coordinate }
        if coords.count >= 2 {
            let polyline = MKPolyline(coordinates: coords, count: coords.count)
            mapView.addOverlay(polyline)
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator: NSObject, MKMapViewDelegate {
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            if let polyline = overlay as? MKPolyline {
                let renderer = MKPolylineRenderer(polyline: polyline)
                renderer.strokeColor = .systemOrange
                renderer.lineWidth = 4
                return renderer
            }
            return MKOverlayRenderer(overlay: overlay)
        }
    }
}

// MARK: - 数据卡片
struct DataCard: View {
    let value: String
    let label: String
    let icon: String
    
    var body: some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.orange)
            Text(value)
                .font(.system(size: 18, weight: .bold, design: .rounded))
            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - 标签芯片
struct TagChip: View {
    let tag: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(tag)
                .font(.subheadline)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(isSelected ? Color.orange : Color(.systemGray5))
                .foregroundColor(isSelected ? .white : .primary)
                .cornerRadius(16)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - 流式布局
struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = arrange(proposal: proposal, subviews: subviews)
        return result.size
    }
    
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = arrange(proposal: proposal, subviews: subviews)
        for (index, position) in result.positions.enumerated() {
            subviews[index].place(at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y), proposal: .unspecified)
        }
    }
    
    private func arrange(proposal: ProposedViewSize, subviews: Subviews) -> (positions: [CGPoint], size: CGSize) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > maxWidth, x > 0 {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            positions.append(CGPoint(x: x, y: y))
            rowHeight = max(rowHeight, size.height)
            x += size.width + spacing
        }
        
        return (positions, CGSize(width: maxWidth, height: y + rowHeight))
    }
}
