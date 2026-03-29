import SwiftUI
import MapKit

struct ExploreView: View {
    @StateObject private var viewModel = ExploreViewModel()
    @State private var searchText = ""
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {
                    // 搜索栏
                    searchBarView
                    
                    // 分类标签
                    categoryView
                    
                    // 路线列表
                    routeListView
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable {
                await viewModel.refresh()
            }
        }
        .task {
            await viewModel.loadRoutes()
        }
        .onChange(of: searchText) { newValue in
            Task {
                if newValue.isEmpty {
                    await viewModel.loadRoutes()
                } else {
                    // 实时搜索
                    viewModel.searchKeyword = newValue
                    await viewModel.searchRoutes()
                }
            }
        }
    }
    
    // MARK: - 搜索栏
    private var searchBarView: some View {
        HStack(spacing: 12) {
            Image(systemName: "magnifyingglass")
                .foregroundColor(.gray)
            
            TextField("搜索路线、城市、关键词", text: $searchText)
                .textFieldStyle(PlainTextFieldStyle())
                .submitLabel(.search)
            
            if !searchText.isEmpty {
                Button {
                    searchText = ""
                    Task {
                        await viewModel.loadRoutes()
                    }
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.gray)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .padding(.horizontal)
        .padding(.vertical, 12)
        .background(Color(.systemBackground))
    }
    
    // MARK: - 分类标签
    private var categoryView: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 12) {
                ForEach(viewModel.categories, id: \.self) { category in
                    CategoryChip(
                        title: category,
                        isSelected: viewModel.selectedCategory == category
                    ) {
                        viewModel.selectCategory(category)
                    }
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 12)
        }
        .background(Color(.systemBackground))
    }
    
    // MARK: - 路线列表
    private var routeListView: some View {
        VStack(alignment: .leading, spacing: 16) {
            // 路线数量提示
            if !viewModel.routes.isEmpty {
                Text("\(viewModel.routes.count) 条路线")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .padding(.horizontal)
                    .padding(.top, 8)
            }
            
            if viewModel.isLoading {
                loadingView
            } else if let error = viewModel.errorMessage {
                errorView(error)
            } else if viewModel.routes.isEmpty {
                emptyView
            } else {
                LazyVStack(spacing: 16) {
                    ForEach(viewModel.routes) { route in
                        NavigationLink(value: route) {
                            RouteCardView(route: route)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
                .padding(.horizontal)
            }
        }
        .padding(.bottom, 20)
        .background(Color(.systemBackground))
        .navigationDestination(for: Route.self) { route in
            RouteDetailView(route: route)
        }
    }
    
    // MARK: - 加载视图
    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text("加载中...")
                .foregroundColor(.secondary)
        }
        .frame(height: 200)
    }
    
    // MARK: - 空视图
    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: "map")
                .font(.system(size: 48))
                .foregroundColor(.gray)
            
            Text("暂无路线")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("试试其他分类或关键词")
                .font(.subheadline)
                .foregroundColor(.gray)
        }
        .frame(height: 200)
    }
    
    // MARK: - 错误视图
    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)
            
            Text(message)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            Button("重试") {
                Task {
                    await viewModel.loadRoutes()
                }
            }
            .buttonStyle(.bordered)
        }
        .frame(height: 200)
    }
}

// MARK: - 分类标签组件
struct CategoryChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(.medium))
                .foregroundColor(isSelected ? .white : .primary)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(
                    Capsule()
                        .fill(isSelected ? Color.orange : Color(.systemGray5))
                )
        }
    }
}

// MARK: - 路线卡片
struct RouteCardView: View {
    let route: Route
    
    var body: some View {
        HStack(spacing: 16) {
            // 图片
            ZStack(alignment: .topTrailing) {
                RoundedRectangle(cornerRadius: 12)
                    .fill(
                        LinearGradient(
                            colors: [.orange.opacity(0.3), .pink.opacity(0.3)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 100, height: 100)
                    .overlay(
                        Image(systemName: "mountain.2.fill")
                            .font(.title)
                            .foregroundColor(.white.opacity(0.6))
                    )
                
                // 难度标签
                if let difficulty = route.difficulty {
                    Text(difficulty.displayText)
                        .font(.caption2.bold())
                        .foregroundColor(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(difficultyColor(difficulty))
                        .cornerRadius(6)
                        .padding(6)
                }
            }
            
            // 信息
            VStack(alignment: .leading, spacing: 8) {
                Text(route.name)
                    .font(.headline)
                    .lineLimit(1)
                
                Text(route.description ?? "暂无描述")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
                
                HStack(spacing: 12) {
                    Label(route.formattedDistance, systemImage: "point.topleft.down.curvedto.point.bottomright.up")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    Label(route.formattedDuration, systemImage: "clock")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                
                // 标签
                if let tags = route.tags {
                    HStack(spacing: 6) {
                        ForEach(tags.prefix(3), id: \.self) { tag in
                            Text(tag)
                                .font(.caption2)
                                .foregroundColor(.orange)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.orange.opacity(0.1))
                                .cornerRadius(4)
                        }
                    }
                }
            }
            
            Spacer()
            
            // 箭头
            Image(systemName: "chevron.right")
                .foregroundColor(.gray)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
    
    private func difficultyColor(_ difficulty: Difficulty) -> Color {
        switch difficulty {
        case .easy: return .green
        case .medium: return .orange
        case .hard: return .red
        }
    }
}

// MARK: - 路线详情页
struct RouteDetailView: View {
    let route: Route
    @State private var detailedRoute: Route?
    @State private var isLoading = true
    @State private var region: MKCoordinateRegion
    
    init(route: Route) {
        self.route = route
        
        // 初始化地图区域（先用深圳默认）
        _region = State(initialValue: MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 22.5, longitude: 114.0),
            span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
        ))
    }
    
    // 路线坐标（转换为火星坐标）
    var routeCoordinates: [CLLocationCoordinate2D] {
        let rawCoords = (detailedRoute?.points ?? route.points)?.map { $0.location.coordinate } ?? []
        if let first = rawCoords.first {
            print("📍 原始坐标: lat=\(first.latitude), lon=\(first.longitude)")
        }
        let converted = CoordinateConverter.wgs84ToGcj02(rawCoords)
        if let first = converted.first {
            print("📍 转换后: lat=\(first.latitude), lon=\(first.longitude)")
        }
        return converted
    }

    // 海拔统计
    var elevationStats: (min: Double, max: Double)? {
        let elevations = (detailedRoute?.points ?? route.points)?.compactMap { $0.elevation } ?? []
        guard let min = elevations.min(), let max = elevations.max() else { return nil }
        return (min, max)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                // 地图视图
                if isLoading {
                    ProgressView("加载地图...")
                        .frame(height: 300)
                        .frame(maxWidth: .infinity)
                        .background(Color(.systemGray6))
                } else {
                    RouteMapView(region: $region, coordinates: routeCoordinates, routeName: route.name)
                        .frame(height: 300)
                }
                
                // 基本信息
                VStack(alignment: .leading, spacing: 12) {
                    Text(route.name)
                        .font(.title.bold())
                    
                    if let description = route.description {
                        Text(description)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    
                    // 统计信息
                    HStack(spacing: 24) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("距离")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text(route.formattedDistance)
                                .font(.headline)
                        }
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("时长")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text(route.formattedDuration)
                                .font(.headline)
                        }
                        
                        if let difficulty = route.difficulty {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("难度")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Text(difficulty.displayText)
                                    .font(.headline)
                                    .foregroundColor(difficultyColor(difficulty))
                            }
                        }
                    }
                    .padding(.vertical, 12)
                    
                    // 标签
                    if let tags = route.tags {
                        HStack(spacing: 8) {
                            ForEach(tags, id: \.self) { tag in
                                Text(tag)
                                    .font(.subheadline)
                                    .foregroundColor(.orange)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color.orange.opacity(0.1))
                                    .cornerRadius(8)
                            }
                        }
                    }
                }
                .padding()
                
                Divider()
                    .padding(.horizontal)

                // 海拔剖面图
                if let points = detailedRoute?.points ?? route.points, points.count > 1 {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("海拔剖面")
                            .font(.headline)

                        ElevationChartView(points: points)
                            .frame(height: 150)
                            .background(Color(.systemGray6))
                            .cornerRadius(8)

                        // 海拔信息
                        HStack {
                            if let stats = elevationStats {
                                Label("最低 \(Int(stats.min))m", systemImage: "arrow.down")
                                    .font(.caption)
                                    .foregroundColor(.blue)
                                Spacer()
                                Label("最高 \(Int(stats.max))m", systemImage: "arrow.up")
                                    .font(.caption)
                                    .foregroundColor(.red)
                                Spacer()
                                Label("爬升 \(Int(stats.max - stats.min))m", systemImage: "figure.hiking")
                                    .font(.caption)
                                    .foregroundColor(.orange)
                            }
                        }
                    }
                    .padding()
                }

                Divider()
                    .padding(.horizontal)

                // 轨迹点信息
                VStack(alignment: .leading, spacing: 12) {
                    Text("路线详情")
                        .font(.title2.bold())
                    
                    HStack {
                        Label("\((detailedRoute?.points ?? route.points)?.count ?? 0) 个轨迹点", systemImage: "location")
                            .foregroundColor(.secondary)
                        
                        Spacer()
                        
                        if let city = route.city {
                            Label(city, systemImage: "building.2")
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    // POI 列表
                    if let pois = detailedRoute?.pois ?? route.pois, !pois.isEmpty {
                        Text("沿途 POI")
                            .font(.headline)
                            .padding(.top, 8)
                        
                        ForEach(pois.prefix(5)) { poi in
                            HStack {
                                Image(systemName: "mappin.circle")
                                    .foregroundColor(.orange)
                                VStack(alignment: .leading) {
                                    Text(poi.name)
                                        .font(.subheadline)
                                    if let category = poi.category {
                                        Text(category)
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                                Spacer()
                                if let distance = poi.distance {
                                    Text("\(Int(distance))m")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                .padding()
                
                Spacer()
                    .frame(height: 20)
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    // TODO: 收藏功能
                } label: {
                    Image(systemName: "heart")
                }
            }
            
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    // TODO: 分享功能
                } label: {
                    Image(systemName: "square.and.arrow.up")
                }
            }
        }
        .task {
            await loadRouteDetail()
        }
    }
    
    private func loadRouteDetail() async {
        do {
            let detail = try await APIService.shared.fetchRoute(id: route.id)
            detailedRoute = detail
            isLoading = false
            
            // 更新地图区域
            if let points = detail.points, !points.isEmpty {
                let rawCoordinates = points.map { $0.location.coordinate }
                print("📍 第一个原始坐标: \(rawCoordinates.first!)")
                
                let coordinates = CoordinateConverter.wgs84ToGcj02(rawCoordinates)
                print("📍 第一个转换坐标: \(coordinates.first!)")
                
                let lats = coordinates.map { $0.latitude }
                let lons = coordinates.map { $0.longitude }
                
                let minLat = lats.min() ?? 0
                let maxLat = lats.max() ?? 0
                let minLon = lons.min() ?? 0
                let maxLon = lons.max() ?? 0
                
                let centerLat = (minLat + maxLat) / 2
                let centerLon = (minLon + maxLon) / 2
                print("📍 地图中心: lat=\(centerLat), lon=\(centerLon)")
                
                region = MKCoordinateRegion(
                    center: CLLocationCoordinate2D(
                        latitude: centerLat,
                        longitude: centerLon
                    ),
                    span: MKCoordinateSpan(
                        latitudeDelta: (maxLat - minLat) * 1.3 + 0.01,
                        longitudeDelta: (maxLon - minLon) * 1.3 + 0.01
                    )
                )
            }
        } catch {
            print("❌ 加载路线详情失败: \(error.localizedDescription)")
            isLoading = false
        }
    }
    
    private func difficultyColor(_ difficulty: Difficulty) -> Color {
        switch difficulty {
        case .easy: return .green
        case .medium: return .orange
        case .hard: return .red
        }
    }
}

// MARK: - 路线地图视图
struct RouteMapView: UIViewRepresentable {
    @Binding var region: MKCoordinateRegion
    let coordinates: [CLLocationCoordinate2D]
    let routeName: String
    
    init(region: Binding<MKCoordinateRegion>, coordinates: [CLLocationCoordinate2D], routeName: String = "路线") {
        self._region = region
        self.coordinates = coordinates
        self.routeName = routeName
    }
    
    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        mapView.region = region
        
        // 设置地图类型（标准地图）
        mapView.mapType = .standard
        
        // 启用交互
        mapView.isZoomEnabled = true
        mapView.isScrollEnabled = true
        mapView.isRotateEnabled = true
        mapView.showsUserLocation = false
        mapView.showsCompass = true
        mapView.showsScale = true
        mapView.showsBuildings = true
        mapView.showsTraffic = false
        
        return mapView
    }
    
    func updateUIView(_ mapView: MKMapView, context: Context) {
        // 更新地图区域
        let currentCenter = mapView.region.center
        let targetCenter = region.center
        
        // 如果区域变化较大，更新地图
        let latDiff = abs(currentCenter.latitude - targetCenter.latitude)
        let lonDiff = abs(currentCenter.longitude - targetCenter.longitude)
        if latDiff > 0.001 || lonDiff > 0.001 {
            mapView.setRegion(region, animated: true)
        }
        
        // 清除旧的覆盖物和注释
        mapView.removeOverlays(mapView.overlays)
        mapView.removeAnnotations(mapView.annotations)
        
        // 添加路线
        if !coordinates.isEmpty {
            let polyline = MKPolyline(coordinates: coordinates, count: coordinates.count)
            mapView.addOverlay(polyline)
            
            // 添加起点标记
            let startAnnotation = MKPointAnnotation()
            startAnnotation.coordinate = coordinates.first!
            startAnnotation.title = "起点"
            startAnnotation.subtitle = routeName
            mapView.addAnnotation(startAnnotation)
            
            // 添加终点标记
            if coordinates.count > 1 {
                let endAnnotation = MKPointAnnotation()
                endAnnotation.coordinate = coordinates.last!
                endAnnotation.title = "终点"
                mapView.addAnnotation(endAnnotation)
            }
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator: NSObject, MKMapViewDelegate {
        var isFirstLoad = true
        
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            if let polyline = overlay as? MKPolyline {
                let renderer = MKPolylineRenderer(polyline: polyline)
                renderer.strokeColor = UIColor.systemOrange
                renderer.lineWidth = 4
                return renderer
            }
            return MKOverlayRenderer(overlay: overlay)
        }
        
        func mapView(_ mapView: MKMapView, viewFor annotation: MKAnnotation) -> MKAnnotationView? {
            let identifier = "RouteAnnotation"
            
            var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier)
            
            if annotationView == nil {
                annotationView = MKMarkerAnnotationView(annotation: annotation, reuseIdentifier: identifier)
            } else {
                annotationView?.annotation = annotation
            }
            
            // 设置标记样式
            if let markerView = annotationView as? MKMarkerAnnotationView {
                if annotation.title == "起点" {
                    markerView.markerTintColor = UIColor.systemGreen
                    markerView.glyphImage = UIImage(systemName: "play.fill")
                } else if annotation.title == "终点" {
                    markerView.markerTintColor = UIColor.systemRed
                    markerView.glyphImage = UIImage(systemName: "flag.fill")
                }
                markerView.canShowCallout = true
            }
            
            return annotationView
        }
    }
}

// MARK: - 海拔剖面图
struct ElevationChartView: View {
    let points: [RoutePoint]

    // 计算距离-海拔数据点
    private var chartData: [(distance: Double, elevation: Double)] {
        var result: [(Double, Double)] = []
        var totalDistance: Double = 0

        for i in 0..<points.count {
            // 获取海拔
            let elevation = points[i].elevation ?? 0

            // 计算累积距离
            if i > 0 {
                let prev = points[i - 1]
                let curr = points[i]
                let lat1 = prev.location.latitude
                let lon1 = prev.location.longitude
                let lat2 = curr.location.latitude
                let lon2 = curr.location.longitude

                // Haversine 公式计算距离
                let R = 6371000.0 // 地球半径（米）
                let dLat = (lat2 - lat1) * .pi / 180
                let dLon = (lon2 - lon1) * .pi / 180
                let a = sin(dLat/2) * sin(dLat/2) +
                        cos(lat1 * .pi / 180) * cos(lat2 * .pi / 180) *
                        sin(dLon/2) * sin(dLon/2)
                let c = 2 * atan2(sqrt(a), sqrt(1-a))
                totalDistance += R * c
            }

            result.append((totalDistance, elevation))
        }
        return result
    }

    private var minElevation: Double {
        chartData.map { $0.elevation }.min() ?? 0
    }

    private var maxElevation: Double {
        chartData.map { $0.elevation }.max() ?? 0
    }

    private var totalDistance: Double {
        chartData.last?.distance ?? 0
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                // 网格线
                Path { path in
                    let hLines = 4
                    for i in 0...hLines {
                        let y = geometry.size.height * CGFloat(i) / CGFloat(hLines)
                        path.move(to: CGPoint(x: 0, y: y))
                        path.addLine(to: CGPoint(x: geometry.size.width, y: y))
                    }
                }
                .stroke(Color.gray.opacity(0.2), lineWidth: 0.5)

                // 海拔曲线
                if chartData.count >= 2 {
                    let elevationRange = maxElevation - minElevation
                    let elevationPadding = max(elevationRange * 0.1, 10)

                    Path { path in
                        for (index, dataPoint) in chartData.enumerated() {
                            let x = geometry.size.width * CGFloat(dataPoint.distance / totalDistance)
                            let normalizedElevation = (dataPoint.elevation - minElevation + elevationPadding) / (elevationRange + 2 * elevationPadding)
                            let y = geometry.size.height * CGFloat(1 - normalizedElevation)

                            if index == 0 {
                                path.move(to: CGPoint(x: x, y: y))
                            } else {
                                path.addLine(to: CGPoint(x: x, y: y))
                            }
                        }
                    }
                    .stroke(
                        LinearGradient(
                            colors: [.blue, .orange],
                            startPoint: .leading,
                            endPoint: .trailing
                        ),
                        lineWidth: 2
                    )

                    // 填充区域
                    Path { path in
                        path.move(to: CGPoint(x: 0, y: geometry.size.height))

                        for dataPoint in chartData {
                            let x = geometry.size.width * CGFloat(dataPoint.distance / totalDistance)
                            let normalizedElevation = (dataPoint.elevation - minElevation + elevationPadding) / (elevationRange + 2 * elevationPadding)
                            let y = geometry.size.height * CGFloat(1 - normalizedElevation)
                            path.addLine(to: CGPoint(x: x, y: y))
                        }

                        path.addLine(to: CGPoint(x: geometry.size.width, y: geometry.size.height))
                        path.closeSubpath()
                    }
                    .fill(
                        LinearGradient(
                            colors: [.orange.opacity(0.3), .blue.opacity(0.1)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                }
            }
        }
        .padding(4)
    }
}

// MARK: - 预览
#Preview {
    ExploreView()
}
