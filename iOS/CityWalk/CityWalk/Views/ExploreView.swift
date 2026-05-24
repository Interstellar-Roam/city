import SwiftUI
import MapKit
import AVFoundation
import AMapFoundationKit
import AMapLocationKit
import MAMapKit

struct ExploreView: View {
    @StateObject private var viewModel = ExploreViewModel()
    @State private var searchText = ""
    
    // AI聊天状态
    @State private var showAIChat = false
    @State private var aiMessages: [AIChatMessage] = []
    @State private var aiInputText = ""
    @State private var currentSessionId: String?  // 当前会话 ID
    @State private var featuredRoutes: [Route] = []
    
    var body: some View {
        NavigationStack {
            ZStack(alignment: .bottomTrailing) {
                ScrollView {
                    VStack(spacing: 0) {
                        // 搜索栏
                        searchBarView
                        
                        // Hero Banner 精选路线
                        if !featuredRoutes.isEmpty {
                            HeroBannerView(routes: featuredRoutes)
                        }
                        
                        // 分类标签
                        categoryView
                        
                        // 路线列表
                        routeListView
                    }
                }
                .background(Color(.systemGroupedBackground))
                
                // AI浮动按钮
                Button {
                    showAIChat = true
                } label: {
                    Image(systemName: "sparkles")
                        .font(.system(size: 24))
                        .foregroundColor(.white)
                        .frame(width: 56, height: 56)
                        .background(
                            LinearGradient(
                                colors: [.purple, .blue],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .clipShape(Circle())
                        .shadow(radius: 4)
                }
                .padding(.trailing, 16)
                .padding(.bottom, 16)
            }
            .navigationTitle("")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable {
                await viewModel.refresh()
            }
            .sheet(isPresented: $showAIChat) {
                AIChatView(
                    messages: $aiMessages,
                    inputText: $aiInputText,
                    currentSessionId: $currentSessionId
                )
            }
        }
        .task {
            // 只在首次加载时调用
            if viewModel.routes.isEmpty {
                await viewModel.loadRoutes()
            }
            // 加载精选路线
            if let featured = try? await APIService.shared.fetchFeaturedRoutes() {
                featuredRoutes = featured
            }
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
                        .buttonStyle(ScaleButtonStyle())
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
            ForEach(0..<3, id: \.self) { _ in
                RouteCardSkeleton()
            }
        }
        .padding(.horizontal)
    }
    
    // MARK: - 空视图
    private var emptyView: some View {
        VStack(spacing: 20) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 40, weight: .light))
                .foregroundColor(.secondary.opacity(0.5))
                .padding(.top, 20)

            Text(searchText.isEmpty ? "暂无路线" : "没有找到匹配路线")
                .font(.headline)
                .foregroundColor(.secondary)

            if !searchText.isEmpty, !featuredRoutes.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("试试这些热门路线")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                        .padding(.horizontal)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 12) {
                            ForEach(featuredRoutes.prefix(3)) { route in
                                NavigationLink(value: route) {
                                    MiniRouteCard(route: route)
                                }
                                .buttonStyle(PlainButtonStyle())
                            }
                        }
                        .padding(.horizontal)
                    }
                }
            } else if searchText.isEmpty {
                Text("换个分类试试")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .frame(minHeight: 200)
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

// MARK: - 12色调色板
private let cardPalette: [(Color, Color)] = [
    (.orange, .pink), (.blue, .purple), (.green, .teal),
    (.red, .orange), (.purple, .blue), (.teal, .green),
    (.pink, .red), (.mint, .blue), (.indigo, .purple),
    (.yellow, .orange), (.cyan, .blue), (.brown, .orange)
]

// MARK: - 按压缩放按钮样式
struct ScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: configuration.isPressed)
    }
}

// MARK: - 路线卡片
struct RouteCardView: View {
    let route: Route
    @State private var isFav: Bool
    @State private var favCount: Int

    init(route: Route) {
        self.route = route
        _isFav = State(initialValue: route.isFavorited ?? false)
        _favCount = State(initialValue: route.favoritesCount ?? 0)
    }

    private var gradientColors: (Color, Color) {
        let idx = abs(route.name.hashValue) % cardPalette.count
        return cardPalette[idx]
    }

    private var gradientPlaceholder: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(
                LinearGradient(
                    colors: [gradientColors.0.opacity(0.3), gradientColors.1.opacity(0.3)],
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
    }

    var body: some View {
        HStack(spacing: 16) {
            // 封面图 / 渐变占位
            ZStack(alignment: .topTrailing) {
                // 有封面 URL → 加载真实图片
                if let coverURL = route.coverImage, let url = URL(string: coverURL) {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .success(let image):
                            image.resizable().scaledToFill()
                                .frame(width: 100, height: 100).cornerRadius(12).clipped()
                        case .failure, .empty:
                            gradientPlaceholder
                        @unknown default:
                            gradientPlaceholder
                        }
                    }
                } else {
                    gradientPlaceholder
                }

                // 难度标签（颜色随难度变化）
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

                if let desc = route.description, !desc.isEmpty {
                    Text(desc)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(2)
                }

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

            // 收藏按钮
            Button(action: toggleFavorite) {
                VStack(spacing: 2) {
                    Image(systemName: isFav ? "heart.fill" : "heart")
                        .font(.title3)
                        .foregroundColor(isFav ? .red : .gray)
                    Text("\(favCount)")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                .frame(width: 44)
            }
            .buttonStyle(.plain)
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

    private func toggleFavorite() {
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()

        // 乐观更新
        let previousFav = isFav
        let previousCount = favCount
        isFav.toggle()
        favCount += isFav ? 1 : -1

        Task {
            do {
                let result = try await APIService.shared.toggleFavorite(routeId: route.id)
                // 用服务端数据修正
                await MainActor.run {
                    isFav = result.favorited
                    favCount = result.favoriteCount
                }
            } catch {
                // 回滚
                await MainActor.run {
                    isFav = previousFav
                    favCount = previousCount
                }
            }
        }
    }
}

// MARK: - Hero Banner 精选路线轮播
struct HeroBannerView: View {
    let routes: [Route]
    @State private var currentIndex = 0
    private let timer = Timer.publish(every: 4, on: .main, in: .common).autoconnect()

    var body: some View {
        TabView(selection: $currentIndex) {
            ForEach(Array(routes.enumerated()), id: \.element.id) { idx, route in
                NavigationLink(value: route) {
                    ZStack(alignment: .bottomLeading) {
                        // 有封面图时显示真实图片，否则渐变色
                        if let coverURL = route.coverImage, !coverURL.isEmpty, let url = URL(string: coverURL) {
                            AsyncImage(url: url) { phase in
                                switch phase {
                                case .success(let image):
                                    image.resizable().scaledToFill()
                                        .aspectRatio(16/9, contentMode: .fit)
                                        .cornerRadius(16).clipped()
                                default:
                                    bannerGradient(idx)
                                }
                            }
                        } else {
                            bannerGradient(idx)
                        }

                        // 底部渐变遮罩
                        LinearGradient(
                            colors: [.clear, .black.opacity(0.6)],
                            startPoint: .center,
                            endPoint: .bottom
                        )
                        .cornerRadius(16)

                        // 文字信息
                        VStack(alignment: .leading, spacing: 4) {
                            Text(route.name)
                                .font(.title3.bold())
                                .foregroundColor(.white)
                            bannerInfoRow(route: route)
                        }
                        .padding(16)
                    }
                }
                .buttonStyle(PlainButtonStyle())
                .padding(.horizontal)
                .tag(idx)
            }
        }
        .tabViewStyle(.page(indexDisplayMode: routes.count > 1 ? .always : .never))
        .frame(height: 220)
        .onReceive(timer) { _ in
            withAnimation(.easeInOut(duration: 0.5)) {
                currentIndex = (currentIndex + 1) % routes.count
            }
        }
    }

    private func bannerGradient(_ idx: Int) -> some View {
        RoundedRectangle(cornerRadius: 16)
            .fill(
                LinearGradient(
                    colors: [
                        Color(hue: Double(idx * 60 % 360) / 360.0, saturation: 0.6, brightness: 0.8),
                        Color(hue: Double((idx * 60 + 30) % 360) / 360.0, saturation: 0.7, brightness: 0.5)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .aspectRatio(16/9, contentMode: .fit)
    }

    private func bannerInfoRow(route: Route) -> some View {
        HStack(spacing: 8) {
            Text(route.formattedDistance)
                .font(.caption)
                .foregroundColor(.white.opacity(0.8))
            if let diff = route.difficulty {
                Text(diff.displayText)
                    .font(.caption2)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(difficultyColor(diff).opacity(0.8))
                    .cornerRadius(4)
                    .foregroundColor(.white)
            }
            if let tags = route.tags, let first = tags.first {
                Text(first)
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.7))
            }
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

// MARK: - 迷你路线卡片（搜索空状态推荐）
struct MiniRouteCard: View {
    let route: Route

    private var gradientColors: (Color, Color) {
        let idx = abs(route.name.hashValue) % cardPalette.count
        return cardPalette[idx]
    }

    private var miniGradientPlaceholder: some View {
        RoundedRectangle(cornerRadius: 10)
            .fill(
                LinearGradient(
                    colors: [gradientColors.0.opacity(0.3), gradientColors.1.opacity(0.3)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(width: 140, height: 80)
            .overlay(
                Image(systemName: "mountain.2.fill")
                    .foregroundColor(.white.opacity(0.5))
            )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if let coverURL = route.coverImage, let url = URL(string: coverURL) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFill()
                            .frame(width: 140, height: 80).cornerRadius(10).clipped()
                    default:
                        miniGradientPlaceholder
                    }
                }
            } else {
                miniGradientPlaceholder
            }

            Text(route.name)
                .font(.caption)
                .lineLimit(1)

            Text(route.formattedDistance)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .frame(width: 140)
        .padding(8)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
    }
}

// MARK: - 路线详情页
struct RouteDetailView: View {
    let route: Route
    @State private var detailedRoute: Route?
    @State private var region: MKCoordinateRegion
    @State private var showNavigation = false
    @State private var showNavigationPrep = false
    @State private var isMapReady = false
    @State private var cachedCoordinates: [CLLocationCoordinate2D] = []  // 缓存转换后的坐标
    @State private var showShareSheet = false
    @State private var showEditSheet = false
    @State private var isFavorited: Bool
    @State private var favCount: Int
    @State private var selectedLayer: MapLayerMode = .standard
    
    init(route: Route) {
        self.route = route
        _isFavorited = State(initialValue: route.isFavorited ?? false)
        _favCount = State(initialValue: route.favoritesCount ?? 0)
        
        // 初始化地图区域（先用深圳默认）
        _region = State(initialValue: MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 22.5, longitude: 114.0),
            span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
        ))
    }
    
    // 路线坐标（使用缓存）
    var routeCoordinates: [CLLocationCoordinate2D] {
        cachedCoordinates
    }

    // 海拔统计
    var elevationStats: (min: Double, max: Double)? {
        let elevations = (detailedRoute?.points ?? route.points)?.compactMap { $0.elevation } ?? []
        guard let min = elevations.min(), let max = elevations.max() else { return nil }
        return (min, max)
    }

    // 导航坐标（使用缓存的坐标）
    var navigationCoordinates: [CLLocationCoordinate2D] {
        cachedCoordinates
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                // 地图视图 — 占屏幕 60%
                ZStack(alignment: .bottomTrailing) {
                    RouteMapView(region: $region, coordinates: routeCoordinates, routeName: route.name, selectedLayer: selectedLayer)
                        .frame(height: UIScreen.main.bounds.height * 0.60)
                        .onAppear {
                            isMapReady = true
                        }

                    // 图层切换按钮（右下角）
                    MapLayerToggle(selectedLayer: $selectedLayer)
                        .padding(.trailing, 12)
                        .padding(.bottom, 48)
                }
                
                // 紧凑信息 + 开始导航（首次可见，不用滑动）
                VStack(alignment: .leading, spacing: 10) {
                    Text(route.name)
                        .font(.title2.bold())
                        .lineLimit(1)
                    
                    if let description = route.description, !description.isEmpty {
                        Text(description)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .lineLimit(2)
                    }
                    
                    // 开始导航按钮
                    Button {
                        showNavigationPrep = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "navigation.fill")
                                .font(.system(size: 16))
                            Text("开始导航")
                                .font(.headline)
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(Color.orange)
                        .cornerRadius(12)
                    }
                    .padding(.top, 4)
                }
                .padding(.horizontal)
                .padding(.top, 16)
                
                Divider()
                    .padding(.horizontal)
                    .padding(.top, 16)
                
                // 以下为可滑动内容 — 上滑查看
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
                .padding(.horizontal)
                .padding(.vertical, 12)
                
                // 标签
                if let tags = route.tags {
                    ScrollView(.horizontal, showsIndicators: false) {
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
                        .padding(.horizontal)
                    }
                }
                
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
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            // 收藏按钮
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    UIImpactFeedbackGenerator(style: .light).impactOccurred()
                    let prev = isFavorited
                    let prevCount = favCount
                    isFavorited.toggle()
                    favCount += isFavorited ? 1 : -1
                    Task {
                        do {
                            let result = try await APIService.shared.toggleFavorite(routeId: route.id)
                            await MainActor.run {
                                isFavorited = result.favorited
                                favCount = result.favoriteCount
                            }
                        } catch {
                            await MainActor.run {
                                isFavorited = prev
                                favCount = prevCount
                            }
                        }
                    }
                } label: {
                    HStack(spacing: 2) {
                        Image(systemName: isFavorited ? "heart.fill" : "heart")
                            .foregroundColor(isFavorited ? .red : .gray)
                        Text("\(favCount)")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
            // 编辑按钮（仅自己的路线）
            if route.createdBy == TokenStorage.shared.getUserId() {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showEditSheet = true
                    } label: {
                        Image(systemName: "pencil")
                    }
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showShareSheet = true
                } label: {
                    Image(systemName: "square.and.arrow.up")
                }
            }
        }
        .task {
            await loadRouteDetail()
        }
        .sheet(isPresented: $showNavigation) {
            RoutePreviewView(routeName: route.name, coordinates: navigationCoordinates, points: detailedRoute?.points ?? route.points ?? [])
        }
        .sheet(isPresented: $showNavigationPrep) {
            if let route = detailedRoute {
                NavigationPrepView(route: route)
            } else {
                NavigationPrepView(route: route)
            }
        }
        .sheet(isPresented: $showShareSheet) {
            ShareCardView(route: route)
        }
        .sheet(isPresented: $showEditSheet) {
            EditRouteView(route: route)
        }
    }
    
    private func loadRouteDetail() async {
        // 先用 route 已有的数据在后台线程转换坐标
        if let points = route.points, !points.isEmpty {
            await convertAndUpdateCoordinates(points)
        }
        
        // 然后异步加载详细数据
        do {
            let detail = try await APIService.shared.fetchRoute(id: route.id)
            detailedRoute = detail
            
            // 如果详细数据有更多点，更新坐标
            if let points = detail.points, !points.isEmpty {
                await convertAndUpdateCoordinates(points)
            }
        } catch {
            NSLog("❌ 加载路线详情失败: %@", error.localizedDescription)
        }
    }
    
    /// 在后台线程转换坐标并更新 UI
    private func convertAndUpdateCoordinates(_ points: [RoutePoint]) async {
        // 在后台线程执行坐标转换
        let coordinates = await Task.detached(priority: .userInitiated) {
            let rawCoords = points.map { $0.location.coordinate }
            print("📍 原始坐标数量: \(rawCoords.count)")
            let converted = CoordinateConverter.wgs84ToGcj02(rawCoords)
            print("📍 转换完成")
            return converted
        }.value
        
        // 在主线程更新 UI
        await MainActor.run {
            self.cachedCoordinates = coordinates
        }
        
        // 更新地图区域
        await updateMapRegion(from: points)
    }
    
    private func updateMapRegion(from points: [RoutePoint]) async {
        // 使用已缓存的坐标，避免重复转换
        let coordinates = cachedCoordinates.isEmpty
            ? CoordinateConverter.wgs84ToGcj02(points.map { $0.location.coordinate })
            : cachedCoordinates
        
        guard !coordinates.isEmpty else { return }
        
        let lats = coordinates.map { $0.latitude }
        let lons = coordinates.map { $0.longitude }
        
        let minLat = lats.min() ?? 0
        let maxLat = lats.max() ?? 0
        let minLon = lons.min() ?? 0
        let maxLon = lons.max() ?? 0
        
        let centerLat = (minLat + maxLat) / 2
        let centerLon = (minLon + maxLon) / 2
        
        await MainActor.run {
            region = MKCoordinateRegion(
                center: CLLocationCoordinate2D(
                    latitude: centerLat,
                    longitude: centerLon
                ),
                span: MKCoordinateSpan(
                    latitudeDelta: max((maxLat - minLat) * 1.3, 0.01),
                    longitudeDelta: max((maxLon - minLon) * 1.3, 0.01)
                )
            )
        }
    }

    private func difficultyColor(_ difficulty: Difficulty) -> Color {
        switch difficulty {
        case .easy: return .green
        case .medium: return .orange
        case .hard: return .red
        }
    }

    /// 简化坐标点（每隔 N 个点取一个）
    private func simplifyCoordinates(_ coords: [CLLocationCoordinate2D], maxPoints: Int) -> [CLLocationCoordinate2D] {
        guard coords.count > maxPoints else { return coords }

        var result: [CLLocationCoordinate2D] = []
        let step = max(1, coords.count / maxPoints)

        for i in stride(from: 0, to: coords.count - 1, by: step) {
            result.append(coords[i])
        }

        // 确保最后一个点被包含
        if let last = coords.last {
            if let lastResult = result.last {
                if last.latitude != lastResult.latitude || last.longitude != lastResult.longitude {
                    result.append(last)
                }
            } else {
                result.append(last)
            }
        }

        return result
    }
}

// MARK: - 路线地图视图（高德版，支持 OCM 等高线叠加）
struct RouteMapView: UIViewRepresentable {
    @Binding var region: MKCoordinateRegion
    let coordinates: [CLLocationCoordinate2D]
    let routeName: String
    let selectedLayer: MapLayerMode
    
    init(region: Binding<MKCoordinateRegion>, coordinates: [CLLocationCoordinate2D], routeName: String = "路线", selectedLayer: MapLayerMode = .standard) {
        self._region = region
        self.coordinates = coordinates
        self.routeName = routeName
        self.selectedLayer = selectedLayer
    }
    
    func makeUIView(context: Context) -> MAMapView {
        AMapServices.shared().apiKey = AppConfig.amapAPIKey
        
        let mapView = MAMapView()
        mapView.delegate = context.coordinator
        
        mapView.mapType = .standard
        mapView.isZoomEnabled = true
        mapView.isScrollEnabled = true
        mapView.isRotateEnabled = true
        mapView.showsUserLocation = false
        mapView.showsCompass = true
        mapView.showsScale = true
        mapView.userTrackingMode = .none
        
        // 设置初始区域
        mapView.setRegion(MACoordinateRegion(
            center: region.center,
            span: MACoordinateSpan(
                latitudeDelta: region.span.latitudeDelta,
                longitudeDelta: region.span.longitudeDelta
            )
        ), animated: false)
        
        return mapView
    }
    
    func updateUIView(_ mapView: MAMapView, context: Context) {
        let coordinator = context.coordinator
        
        // 更新区域
        let currentCenter = mapView.region.center
        let targetCenter = region.center
        let latDiff = abs(currentCenter.latitude - targetCenter.latitude)
        let lonDiff = abs(currentCenter.longitude - targetCenter.longitude)
        if latDiff > 0.001 || lonDiff > 0.001 {
            mapView.setRegion(MACoordinateRegion(
                center: targetCenter,
                span: MACoordinateSpan(
                    latitudeDelta: region.span.latitudeDelta,
                    longitudeDelta: region.span.longitudeDelta
                )
            ), animated: true)
        }
        
        // 更新路线覆盖物（仅在坐标变化时）
        let coordsChanged = coordinator.lastPreviewCoords.count != coordinates.count
            || (coordinates.count > 0 && (coordinator.lastPreviewCoords.first?.latitude != coordinates.first?.latitude
                || coordinator.lastPreviewCoords.last?.longitude != coordinates.last?.longitude))
        if coordsChanged {
            coordinator.updatePreviewOverlays(mapView: mapView, coordinates: coordinates, routeName: routeName)
            coordinator.lastPreviewCoords = coordinates
        }
        
        // 更新 OCM 图层
        if coordinator.lastPreviewLayer != selectedLayer {
            coordinator.updatePreviewLayer(mapView: mapView, selectedLayer: selectedLayer)
            coordinator.lastPreviewLayer = selectedLayer
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator: NSObject, MAMapViewDelegate {
        var lastPreviewCoords: [CLLocationCoordinate2D] = []
        var lastPreviewLayer: MapLayerMode = .standard
        
        func updatePreviewOverlays(mapView: MAMapView, coordinates: [CLLocationCoordinate2D], routeName: String) {
            mapView.removeOverlays(mapView.overlays)
            mapView.removeAnnotations(mapView.annotations)
            
            guard !coordinates.isEmpty else { return }
            
            // 路线
            var coords = coordinates
            if let polyline = MAPolyline(coordinates: &coords, count: UInt(coords.count)) {
                mapView.add(polyline)
            }
            
            // 起点
            let startAnnotation = MAPointAnnotation()
            startAnnotation.coordinate = coordinates.first!
            startAnnotation.title = "起点"
            mapView.addAnnotation(startAnnotation)
            
            // 终点
            if coordinates.count > 1 {
                let endAnnotation = MAPointAnnotation()
                endAnnotation.coordinate = coordinates.last!
                endAnnotation.title = "终点"
                mapView.addAnnotation(endAnnotation)
            }
        }
        
        func updatePreviewLayer(mapView: MAMapView, selectedLayer: MapLayerMode) {
            let existingOCM = mapView.overlays.filter { ($0 as? OCMTileOverlay) != nil }
            if !existingOCM.isEmpty {
                mapView.removeOverlays(existingOCM)
            }
            if selectedLayer == .contour {
                mapView.add(OCMTileOverlay.create())
            }
        }
        
        func mapView(_ mapView: MAMapView!, rendererFor overlay: MAOverlay!) -> MAOverlayRenderer! {
            if let polyline = overlay as? MAPolyline {
                let renderer = MAPolylineRenderer(overlay: polyline)
                renderer?.strokeColor = UIColor.systemOrange
                renderer?.lineWidth = 4
                return renderer
            }
            if let tileOverlay = overlay as? MATileOverlay {
                return MATileOverlayRenderer(tileOverlay: tileOverlay)
            }
            return nil
        }
        
        func mapView(_ mapView: MAMapView!, viewFor annotation: MAAnnotation!) -> MAAnnotationView! {
            let identifier = "RoutePreviewAnnotation"
            var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier) as? MAPinAnnotationView
            
            if annotationView == nil {
                annotationView = MAPinAnnotationView(annotation: annotation, reuseIdentifier: identifier)
            } else {
                annotationView?.annotation = annotation
            }
            
            if annotation.title == "起点" {
                annotationView?.pinColor = .green
            } else if annotation.title == "终点" {
                annotationView?.pinColor = .red
            }
            
            annotationView?.canShowCallout = true
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

// MARK: - 路线预览视图
struct RoutePreviewView: View {
    let routeName: String
    let coordinates: [CLLocationCoordinate2D]
    let points: [RoutePoint]  // 添加原始轨迹点数据
    @Environment(\.dismiss) var dismiss
    @State private var progress: Double = 0.0  // 0.0 到 1.0
    @State private var region: MKCoordinateRegion
    @State private var isPlaying = false
    @State private var timer: Timer?
    @State private var completedDistance: Double = 0.0
    @State private var isPausedAtSpecialPoint = false  // 是否在特殊点位暂停
    @State private var specialPointMessage: String? = nil  // 特殊点位提示信息
    @State private var hasShownMaxElevation = false  // 是否已显示最高点
    @State private var hasShownMaxSpeed = false  // 是否已显示最快点
    @State private var lastSpecialPointIndex: Int? = nil  // 上一次触发暂停的特殊点索引
    
    // 配置：特殊点位暂停时间（秒）
    private let specialPointPauseDuration: Double = 1.0

    // 路线边界
    private let routeBounds: (minLat: Double, maxLat: Double, minLon: Double, maxLon: Double, centerLat: Double, centerLon: Double, latDelta: Double, lonDelta: Double)

    // 计算最高海拔点
    private var maxElevationPoint: (index: Int, elevation: Double)? {
        let elevations = points.enumerated().compactMap { (index, point) -> (Int, Double)? in
            guard let elev = point.elevation else { return nil }
            return (index, elev)
        }
        guard let max = elevations.max(by: { $0.1 < $1.1 }) else { return nil }
        return (max.0, max.1)
    }

    // 计算最快速度点
    private var maxSpeedPoint: (index: Int, speed: Double)? {
        var maxSpeed: Double = 0
        var maxIndex: Int = 0

        for i in 1..<points.count {
            let prev = points[i-1]
            let curr = points[i]

            // 计算距离
            let dist = distanceBetween(prev.location.coordinate, curr.location.coordinate)

            // 计算时间差
            if let prevTime = prev.timestamp, let currTime = curr.timestamp {
                let timeInterval = currTime.timeIntervalSince(prevTime)
                if timeInterval > 0 {
                    let speed = dist / timeInterval  // 米/秒
                    if speed > maxSpeed {
                        maxSpeed = speed
                        maxIndex = i
                    }
                }
            }
        }

        return maxSpeed > 0 ? (maxIndex, maxSpeed) : nil
    }

    init(routeName: String, coordinates: [CLLocationCoordinate2D], points: [RoutePoint]) {
        self.routeName = routeName
        self.coordinates = coordinates
        self.points = points

        // 计算路线边界
        if !coordinates.isEmpty {
            let lats = coordinates.map { $0.latitude }
            let lons = coordinates.map { $0.longitude }
            let minLat = lats.min() ?? 0
            let maxLat = lats.max() ?? 0
            let minLon = lons.min() ?? 0
            let maxLon = lons.max() ?? 0
            let latDelta = (maxLat - minLat) * 1.5 + 0.01
            let lonDelta = (maxLon - minLon) * 1.5 + 0.01

            self.routeBounds = (minLat, maxLat, minLon, maxLon, (minLat + maxLat) / 2, (minLon + maxLon) / 2, latDelta, lonDelta)

            // 初始化地图区域 - 显示整条路线
            _region = State(initialValue: MKCoordinateRegion(
                center: CLLocationCoordinate2D(
                    latitude: (minLat + maxLat) / 2,
                    longitude: (minLon + maxLon) / 2
                ),
                span: MKCoordinateSpan(
                    latitudeDelta: latDelta,
                    longitudeDelta: lonDelta
                )
            ))
        } else {
            self.routeBounds = (0, 0, 0, 0, 22.5, 114.0, 0.1, 0.1)
            _region = State(initialValue: MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: 22.5, longitude: 114.0),
                span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
            ))
        }
    }

    // 计算总距离（米）
    private var totalDistance: Double {
        var distance: Double = 0
        for i in 1..<coordinates.count {
            distance += distanceBetween(coordinates[i-1], coordinates[i])
        }
        return distance
    }

    // 当前点索引（基于进度）
    private var currentPointIndex: Int {
        let index = Int(progress * Double(max(0, coordinates.count - 1)))
        return min(index, coordinates.count - 1)
    }

    // 计算经过的时间（秒）
    private var elapsedSeconds: Int {
        // 方法1: 如果有 timestamp 数据，使用实际时间
        guard currentPointIndex > 0, currentPointIndex < points.count else { return 0 }

        var totalSeconds: Double = 0
        for i in 1...currentPointIndex {
            let prev = points[i-1]
            let curr = points[i]
            if let prevTime = prev.timestamp, let currTime = curr.timestamp {
                totalSeconds += currTime.timeIntervalSince(prevTime)
            }
        }

        // 如果有实际时间数据，返回实际时间
        if totalSeconds > 0 {
            return Int(totalSeconds)
        }

        // 方法2: 否则根据进度比例估算时间（假设平均步行速度 5km/h）
        let estimatedTotalMinutes = Int((totalDistance / 1000) / 5.0 * 60) // 总时长（分钟）
        return Int(Double(estimatedTotalMinutes) * progress * 60)
    }

    // 格式化时长为 HH:MM:SS
    private var formattedDuration: String {
        let totalSeconds = elapsedSeconds
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        let seconds = totalSeconds % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    var body: some View {
        NavigationStack {
            ZStack(alignment: .bottomLeading) {
                // 地图
                NavigationMapView(
                    region: region,
                    coordinates: coordinates,
                    currentIndex: currentPointIndex,
                    isPlaying: isPlaying,
                    maxElevationIndex: maxElevationPoint?.index,
                    maxSpeedIndex: maxSpeedPoint?.index,
                    maxElevationValue: maxElevationPoint?.elevation,
                    maxSpeedValue: maxSpeedPoint?.speed
                )
                .ignoresSafeArea()
                
                // 特殊点位提示
                if let message = specialPointMessage {
                    VStack {
                        Spacer()
                        HStack {
                            Spacer()
                            Text(message)
                                .font(.system(size: 24, weight: .bold))
                                .foregroundColor(.white)
                                .padding(.horizontal, 24)
                                .padding(.vertical, 12)
                                .background(
                                    Capsule()
                                        .fill(Color.black.opacity(0.8))
                                )
                                .transition(.scale.combined(with: .opacity))
                            Spacer()
                        }
                        Spacer()
                            .frame(height: 150)  // 距离底部的距离
                    }
                    .animation(.easeInOut(duration: 0.3), value: specialPointMessage)
                }

                // 顶部信息栏
                VStack {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(routeName)
                                .font(.headline)
                            Text("总距离: \(String(format: "%.1f", totalDistance / 1000)) km")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                        .padding()
                        .background(Color(.systemBackground).opacity(0.95))
                        .cornerRadius(12)
                        .shadow(radius: 4)

                        Spacer()
                    }
                    .padding()

                    Spacer()

                    // 底部统计信息（右侧展示）
                    // 右侧动态统计
                    VStack(alignment: .trailing, spacing: 4) {
                        Text("\(String(format: "%.2f", completedDistance / 1000)) 公里")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundColor(.white)
                        Text(formattedDuration)
                            .font(.system(size: 14))
                            .foregroundColor(.white.opacity(0.8))
                    }
                    .padding()
                    .background(Color.black.opacity(0.8))
                    .cornerRadius(12)
                    .padding()
                }

                // 左下角预览按钮
                Button(action: {
                    if isPlaying {
                        pausePreview()
                    } else {
                        startPreview()
                    }
                }) {
                    HStack(spacing: 8) {
                        Image(systemName: isPlaying ? "pause.fill" : "play.fill")
                            .font(.title2)
                        Text(isPlaying ? "暂停" : "预览")
                            .fontWeight(.semibold)
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 24)
                    .padding(.vertical, 16)
                    .background(Color.orange)
                    .cornerRadius(30)
                    .shadow(radius: 4)
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        timer?.invalidate()
                        dismiss()
                    } label: {
                        Image(systemName: "xmark")
                    }
                }
            }
            .onAppear {
                // 自动开始预览
                startPreview()
            }
            .onDisappear {
                timer?.invalidate()
            }
        }
    }

    private func startPreview() {
        guard !coordinates.isEmpty else { return }
        isPlaying = true

        // 如果已完成，从头开始
        if progress >= 1.0 {
            progress = 0
            completedDistance = 0
            isPausedAtSpecialPoint = false
            specialPointMessage = nil
            hasShownMaxElevation = false
            hasShownMaxSpeed = false
            lastSpecialPointIndex = nil
            // 重置为全局视图
            region = MKCoordinateRegion(
                center: CLLocationCoordinate2D(latitude: routeBounds.centerLat, longitude: routeBounds.centerLon),
                span: MKCoordinateSpan(latitudeDelta: routeBounds.latDelta, longitudeDelta: routeBounds.lonDelta)
            )
        }

        // 每0.05秒更新一次
        timer = Timer.scheduledTimer(withTimeInterval: 0.066, repeats: true) { _ in
            // 如果在特殊点位暂停，跳过此次更新
            if isPausedAtSpecialPoint {
                return
            }
            
            // 每次增加进度
            let step = 0.005  // 提高预览速度
            let newProgress = min(progress + step, 1.0)
            let newIndex = Int(newProgress * Double(max(0, coordinates.count - 1)))
            let oldIndex = currentPointIndex
            
            // 检查是否到达特殊点位（检测跨越）
            var messages: [(String, Int)] = []  // (消息, 索引)
            
            // 检查最高点（还未显示过，且索引跨越了该点）
            if let maxElev = maxElevationPoint, !hasShownMaxElevation {
                if newIndex >= maxElev.index && oldIndex < maxElev.index {
                    messages.append(("最高 \(Int(maxElev.elevation))m", maxElev.index))
                    hasShownMaxElevation = true
                }
            }
            
            // 检查最快点（还未显示过，且索引跨越了该点）
            if let maxSpd = maxSpeedPoint, !hasShownMaxSpeed {
                if newIndex >= maxSpd.index && oldIndex < maxSpd.index {
                    messages.append(("最快 \(String(format: "%.1f", maxSpd.speed * 3.6))km/h", maxSpd.index))
                    hasShownMaxSpeed = true
                }
            }
            
            // 如果需要暂停
            if !messages.isEmpty {
                isPausedAtSpecialPoint = true
                let firstMessage = messages[0].0
                specialPointMessage = firstMessage
                
                // 更新进度（保持在特殊点）
                progress = newProgress
                completedDistance = totalDistance * progress
                
                // 如果有多个消息（同一点），依次显示
                if messages.count > 1 {
                    // 先显示第一个消息
                    DispatchQueue.main.asyncAfter(deadline: .now() + specialPointPauseDuration) {
                        // 显示第二个消息
                        let secondMessage = messages[1].0
                        specialPointMessage = secondMessage
                        
                        DispatchQueue.main.asyncAfter(deadline: .now() + specialPointPauseDuration) {
                            isPausedAtSpecialPoint = false
                            specialPointMessage = nil
                        }
                    }
                } else {
                    // 只有一个消息
                    DispatchQueue.main.asyncAfter(deadline: .now() + specialPointPauseDuration) {
                        isPausedAtSpecialPoint = false
                        specialPointMessage = nil
                    }
                }
            } else {
                // 更新进度
                progress = newProgress
                completedDistance = totalDistance * progress
            }

            // 更新地图区域 - 跟随位置但保持全局视野
            if progress < 1.0 {
                updateRegion()
            }

            // 预览完成，显示整条路线
            if progress >= 1.0 {
                timer?.invalidate()
                timer = nil
                isPlaying = false

                // 动画切换到全局视图
                withAnimation(.easeInOut(duration: 1.0)) {
                    region = MKCoordinateRegion(
                        center: CLLocationCoordinate2D(latitude: routeBounds.centerLat, longitude: routeBounds.centerLon),
                        span: MKCoordinateSpan(latitudeDelta: routeBounds.latDelta, longitudeDelta: routeBounds.lonDelta)
                    )
                }
                print("✅ 预览完成")
            }
        }
    }

    // 更新地图区域 - 跟随位置但保持大范围视野
    private func updateRegion() {
        let idx = currentPointIndex
        guard idx < coordinates.count else { return }

        let currentCoord = coordinates[idx]

        // 保持路线的全局视野（使用路线边界的55%）
        let spanScale: Double = 0.55
        let latDelta = routeBounds.latDelta * spanScale
        let lonDelta = routeBounds.lonDelta * spanScale

        // 平滑过渡
        withAnimation(.linear(duration: 0.066)) {
            region = MKCoordinateRegion(
                center: currentCoord,
                span: MKCoordinateSpan(latitudeDelta: latDelta, longitudeDelta: lonDelta)
            )
        }
    }

    private func pausePreview() {
        isPlaying = false
        timer?.invalidate()
        timer = nil
    }

    // 计算两点间距离（米）
    private func distanceBetween(_ from: CLLocationCoordinate2D, _ to: CLLocationCoordinate2D) -> Double {
        let R = 6371000.0
        let lat1 = from.latitude * .pi / 180
        let lat2 = to.latitude * .pi / 180
        let deltaLat = (to.latitude - from.latitude) * .pi / 180
        let deltaLon = (to.longitude - from.longitude) * .pi / 180

        let a = sin(deltaLat/2) * sin(deltaLat/2) +
                cos(lat1) * cos(lat2) *
                sin(deltaLon/2) * sin(deltaLon/2)
        let c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c
    }
}

// MARK: - 导航地图视图
struct NavigationMapView: UIViewRepresentable {
    let region: MKCoordinateRegion
    let coordinates: [CLLocationCoordinate2D]
    let currentIndex: Int
    let isPlaying: Bool
    let maxElevationIndex: Int?
    let maxSpeedIndex: Int?
    let maxElevationValue: Double?  // 最高海拔值
    let maxSpeedValue: Double?  // 最快速度值

    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        mapView.mapType = .standard
        mapView.isZoomEnabled = true
        mapView.isScrollEnabled = true
        mapView.isRotateEnabled = true
        mapView.showsUserLocation = false
        mapView.showsCompass = true
        mapView.showsScale = true

        return mapView
    }

    func updateUIView(_ mapView: MKMapView, context: Context) {
        // 设置地图区域（全局预览）
        mapView.setRegion(region, animated: false)

        // 清除旧的覆盖物和注释
        mapView.removeOverlays(mapView.overlays)
        mapView.removeAnnotations(mapView.annotations)

        // 绘制完整路线（灰色）
        if !coordinates.isEmpty {
            let fullPolyline = MKPolyline(coordinates: coordinates, count: coordinates.count)
            fullPolyline.title = "full"
            mapView.addOverlay(fullPolyline)
        }

        // 绘制已走过的路线（绿色）
        if currentIndex > 0 {
            let completedCoords = Array(coordinates[0...currentIndex])
            let completedPolyline = MKPolyline(coordinates: completedCoords, count: completedCoords.count)
            completedPolyline.title = "completed"
            mapView.addOverlay(completedPolyline)
        }

        // 添加最高海拔标记（经过后一直显示）
        if let maxElevIdx = maxElevationIndex, maxElevIdx < coordinates.count, 
           let elevValue = maxElevationValue, currentIndex >= maxElevIdx {
            let annotation = MKPointAnnotation()
            annotation.coordinate = coordinates[maxElevIdx]
            annotation.title = "最高点"
            annotation.subtitle = "\(Int(elevValue))m"
            mapView.addAnnotation(annotation)
        }

        // 添加最快速度标记（经过后一直显示）
        if let maxSpdIdx = maxSpeedIndex, maxSpdIdx < coordinates.count, 
           let spdValue = maxSpeedValue, currentIndex >= maxSpdIdx {
            let annotation = MKPointAnnotation()
            annotation.coordinate = coordinates[maxSpdIdx]
            annotation.title = "最快点"
            annotation.subtitle = "\(String(format: "%.1f", spdValue * 3.6))km/h"
            mapView.addAnnotation(annotation)
        }

        // 添加当前位置标记（带方向的小箭头）
        if currentIndex < coordinates.count {
            let annotation = DirectionAnnotation()
            annotation.coordinate = coordinates[currentIndex]
            annotation.title = "当前位置"

            // 计算方向（朝向下一个点）
            if currentIndex < coordinates.count - 1 {
                let nextCoord = coordinates[currentIndex + 1]
                let direction = bearing(from: coordinates[currentIndex], to: nextCoord)
                annotation.heading = direction
            }

            mapView.addAnnotation(annotation)
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    // 计算两点间的方位角（度）
    private func bearing(from: CLLocationCoordinate2D, to: CLLocationCoordinate2D) -> Double {
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

    class Coordinator: NSObject, MKMapViewDelegate {
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            if let polyline = overlay as? MKPolyline {
                let renderer = MKPolylineRenderer(polyline: polyline)

                if polyline.title == "completed" {
                    // 已走过的路线 - 绿色
                    renderer.strokeColor = UIColor.systemGreen
                    renderer.lineWidth = 5
                } else {
                    // 完整路线 - 灰色
                    renderer.strokeColor = UIColor.systemGray.withAlphaComponent(0.5)
                    renderer.lineWidth = 3
                }

                return renderer
            }
            return MKOverlayRenderer(overlay: overlay)
        }

        func mapView(_ mapView: MKMapView, viewFor annotation: MKAnnotation) -> MKAnnotationView? {
            // 处理方向标注（当前位置）
            if let directionAnnotation = annotation as? DirectionAnnotation {
                let identifier = "DirectionAnnotation"

                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier)

                if annotationView == nil {
                    annotationView = MKAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }

                // 创建小箭头图像
                let config = UIImage.SymbolConfiguration(pointSize: 12, weight: .bold)
                let image = UIImage(systemName: "arrowtriangle.up.fill", withConfiguration: config)?
                    .withTintColor(.systemOrange, renderingMode: .alwaysOriginal)

                if let heading = directionAnnotation.heading {
                    annotationView?.image = image?.rotated(byDegrees: heading)
                } else {
                    annotationView?.image = image
                }

                annotationView?.centerOffset = .zero
                return annotationView
            }

            // 处理指标标注
            if let title = annotation.title {
                let identifier = "MarkerAnnotation"
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier) as? MKMarkerAnnotationView

                if annotationView == nil {
                    annotationView = MKMarkerAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }

                if title == "最高点" {
                    annotationView?.markerTintColor = UIColor.systemRed
                    annotationView?.glyphImage = UIImage(systemName: "mountain.2.fill")
                } else if title == "最快点" {
                    annotationView?.markerTintColor = UIColor.systemBlue
                    annotationView?.glyphImage = UIImage(systemName: "wind")
                }

                return annotationView
            }

            return nil
        }
    }
}

// 带方向的标注
class DirectionAnnotation: NSObject, MKAnnotation {
    var coordinate: CLLocationCoordinate2D
    var title: String?
    var heading: Double?

    override init() {
        self.coordinate = CLLocationCoordinate2D(latitude: 0, longitude: 0)
        super.init()
    }
}

// 扩展：旋转图像
extension UIImage {
    func rotated(byDegrees degrees: CGFloat) -> UIImage? {
        let radians = degrees * .pi / 180

        var newSize = CGRect(origin: .zero, size: self.size)
            .applying(CGAffineTransform(rotationAngle: radians))
            .integral.size
        newSize.width = floor(newSize.width)
        newSize.height = floor(newSize.height)

        UIGraphicsBeginImageContextWithOptions(newSize, false, self.scale)
        let context = UIGraphicsGetCurrentContext()

        context?.translateBy(x: newSize.width / 2, y: newSize.height / 2)
        context?.rotate(by: radians)

        self.draw(in: CGRect(
            x: -self.size.width / 2,
            y: -self.size.height / 2,
            width: self.size.width,
            height: self.size.height
        ))

        let rotatedImage = UIGraphicsGetImageFromCurrentImageContext()
        UIGraphicsEndImageContext()

        return rotatedImage
    }
}

// MARK: - AI聊天消息模型
struct AIChatMessage: Identifiable {
    let id = UUID()
    var content: String
    let isUser: Bool
    let timestamp = Date()
    var isStreaming = false
    var recommendedRoutes: [AIRouteRecommend] = []  // 推荐路线列表
}

// MARK: - AI聊天视图
struct AIChatView: View {
    @Binding var messages: [AIChatMessage]
    @Binding var inputText: String
    @Binding var currentSessionId: String?  // 当前会话ID
    @Environment(\.dismiss) var dismiss
    @State private var refreshTrigger = 0  // 用于强制刷新视图
    @State private var selectedRouteId: RouteIdWrapper?  // 选中的路线ID

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // 消息列表
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            ForEach(messages) { message in
                                MessageBubble(message: message) { route in
                                    // 点击路线卡片，设置导航
                                    NSLog("🗺️ 点击路线: %@ (id=%@)", route.name, route.id)
                                    selectedRouteId = RouteIdWrapper(route.id)
                                }
                                .id("\(message.id.uuidString)-\(refreshTrigger)")
                            }
                        }
                        .padding()
                    }
                    .onChange(of: refreshTrigger) { _ in
                        if let last = messages.last {
                            withAnimation {
                                proxy.scrollTo(last.id, anchor: .bottom)
                            }
                        }
                    }
                }

                Divider()

                // 输入栏
                HStack(spacing: 12) {
                    // 输入框
                    HStack(spacing: 8) {
                        TextField("问问 AI 助手...", text: $inputText)
                            .textFieldStyle(.plain)
                            .onSubmit {
                                sendMessage()
                            }
                        
                        if !inputText.isEmpty {
                            Button {
                                inputText = ""
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.gray)
                                    .font(.system(size: 16))
                            }
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(Color(.systemGray6))
                    .cornerRadius(20)
                    
                    // 发送按钮
                    Button {
                        sendMessage()
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 36))
                            .foregroundColor(inputText.isEmpty ? .gray.opacity(0.3) : .blue)
                    }
                    .disabled(inputText.isEmpty)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color(.systemBackground))
            }
            .navigationTitle("AI助手")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("新会话") {
                        // 清空当前会话
                        messages = []
                        currentSessionId = nil
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("关闭") {
                        dismiss()
                    }
                }
            }
            .navigationDestination(for: Route.self) { route in
                RouteDetailView(route: route)
            }
            // 使用 sheet 显示路线详情
            .sheet(item: $selectedRouteId) { wrapper in
                RouteDetailSheet(routeId: wrapper.id)
            }
        }
    }

    private func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespaces).isEmpty else { return }

        let userMessage = AIChatMessage(content: inputText, isUser: true)
        messages.append(userMessage)

        let aiMessage = AIChatMessage(content: "", isUser: false, isStreaming: true)
        let aiMessageId = aiMessage.id
        messages.append(aiMessage)
        
        let query = inputText
        inputText = ""

        Task { @MainActor in
            do {
                try await APIService.shared.streamSearch(
                    query: query,
                    sessionId: currentSessionId
                ) { event in
                    Task { @MainActor in
                        handleEvent(event, messageId: aiMessageId)
                    }
                }
            } catch {
                if let index = messages.firstIndex(where: { $0.id == aiMessageId }) {
                    messages[index].content = "抱歉，连接失败：\(error.localizedDescription)"
                    messages[index].isStreaming = false
                }
            }
        }
    }

    private func handleEvent(_ event: AIStreamEvent, messageId: UUID) {
        guard let index = messages.firstIndex(where: { $0.id == messageId }) else {
            return
        }

        // 创建消息的副本
        var updatedMessage = messages[index]

        switch event.eventType {
        case .text:
            if let content = event.content {
                updatedMessage.content += content
            }
        case .toolResult:
            // tool_result 是中间结果，不再直接用于显示
            NSLog("📥 收到 tool_result: name=%@, routes数量=%d", event.name ?? "nil", event.routes?.count ?? -1)
        case .routeRecommendations:
            // 最终推荐的路线数据
            if let routes = event.routes, !routes.isEmpty {
                NSLog("🎯 收到最终推荐路线: %d 条", routes.count)
                for (idx, route) in routes.enumerated() {
                    NSLog("  路线[%d]: %@ (id=%@)", idx, route.name, route.id)
                }
                updatedMessage.recommendedRoutes = routes
            } else {
                NSLog("⚠️ route_recommendations 返回空结果")
            }
        case .done:
            NSLog("🎯 handleEvent: 收到 done 事件")
            updatedMessage.isStreaming = false
            // 保存会话 ID
            if let sessionId = event.sessionId {
                currentSessionId = sessionId
                NSLog("📝 保存会话 ID: %@", sessionId)
            }
        case .error:
            if let errorMessage = event.message {
                updatedMessage.content = "错误: \(errorMessage)"
            }
            updatedMessage.isStreaming = false
        default:
            break
        }

        // 创建新数组并重新赋值以触发更新
        var newMessages = messages
        newMessages[index] = updatedMessage
        messages = newMessages

        // 强制刷新视图
        refreshTrigger += 1

        NSLog("🎯 handleEvent: 消息已更新，当前 isStreaming = %d, refreshTrigger = %d, routes = %d", messages[index].isStreaming, refreshTrigger, messages[index].recommendedRoutes.count)
    }

    /// 按 AI 文本中提到的顺序重新排列路线
    private func reorderRoutesByText(routes: [AIRouteRecommend], text: String) -> [AIRouteRecommend] {
        // 从 AI 文本中提取路线名称
        // 格式1: ## 1️⃣ 路线名称 🦆 或 ## 1️⃣ 路线名称
        // 格式2: **路线名称**
        
        var orderedNames: [String] = []
        
        // 方法1: 提取 ## 或 ### 数字️⃣ 后面的路线名称
        let headingPattern = #"#{2,3}\s*[\d]+️⃣\s*([^\n⭐🦆🚶🏔️🌊]+)"#
        if let regex = try? NSRegularExpression(pattern: headingPattern) {
            let range = NSRange(text.startIndex..., in: text)
            let matches = regex.matches(in: text, range: range)
            for match in matches {
                if let nameRange = Range(match.range(at: 1), in: text) {
                    let name = String(text[nameRange]).trimmingCharacters(in: .whitespaces)
                    if !name.isEmpty && !orderedNames.contains(name) {
                        orderedNames.append(name)
                    }
                }
            }
        }
        
        // 方法2: 提取 **路线名称** 格式（作为补充）
        let boldPattern = #"\*\*([^*]+)\*\*"#
        if let regex = try? NSRegularExpression(pattern: boldPattern) {
            let range = NSRange(text.startIndex..., in: text)
            let matches = regex.matches(in: text, range: range)
            for match in matches {
                if let nameRange = Range(match.range(at: 1), in: text) {
                    let name = String(text[nameRange]).trimmingCharacters(in: .whitespaces)
                    // 过滤掉非路线名称
                    if name.count > 2 && !name.contains("公里") && !name.contains("米") && 
                       !name.contains("小时") && !name.contains("分钟") &&
                       !name.hasPrefix("距离") && !name.hasPrefix("爬升") && 
                       !name.hasPrefix("预计") && !name.hasPrefix("标签") &&
                       !name.hasPrefix("难度") && !name.hasPrefix("起点") &&
                       !name.hasPrefix("终点") && !name.hasPrefix("简单") &&
                       !name.hasPrefix("中等") && !name.hasPrefix("困难") &&
                       !orderedNames.contains(name) {
                        orderedNames.append(name)
                    }
                }
            }
        }

        NSLog("📝 AI 文本中提取的名称: %@", orderedNames.joined(separator: ", "))

        // 按文本顺序排列路线
        var reordered: [AIRouteRecommend] = []
        var remaining = routes

        for name in orderedNames {
            // 尝试匹配路线名称（模糊匹配）
            if let idx = remaining.firstIndex(where: { route in
                let routeName = route.name.lowercased()
                let searchName = name.lowercased()
                
                // 直接包含
                if routeName.contains(searchName) || searchName.contains(routeName) {
                    return true
                }
                
                // 提取关键词匹配
                let keywords = extractChineseKeywords(from: searchName)
                for keyword in keywords {
                    if routeName.contains(keyword) {
                        return true
                    }
                }
                
                return false
            }) {
                reordered.append(remaining.remove(at: idx))
            }
        }

        // 如果有匹配到的路线，只显示匹配的；否则显示所有路线
        if reordered.isEmpty {
            NSLog("📝 未匹配到路线，显示所有 %d 条路线", routes.count)
            return routes
        } else {
            NSLog("📝 匹配到 %d 条路线: %@", reordered.count, reordered.map { $0.name }.joined(separator: ", "))
            return reordered
        }
    }
    
    /// 提取中文关键词
    private func extractChineseKeywords(from text: String) -> [String] {
        var keywords: [String] = []
        
        // 常见地点关键词
        let locationPatterns = ["福田", "后海", "深圳湾", "塘朗", "石岩湖", "人才公园", "高新园", "坪洲"]
        for pattern in locationPatterns {
            if text.contains(pattern.lowercased()) {
                keywords.append(pattern.lowercased())
            }
        }
        
        // 提取2-4个连续中文字符作为关键词
        let chinesePattern = "[\\u4e00-\\u9fa5]{2,4}"
        if let regex = try? NSRegularExpression(pattern: chinesePattern) {
            let range = NSRange(text.startIndex..., in: text)
            let matches = regex.matches(in: text, range: range)
            for match in matches {
                if let keywordRange = Range(match.range(at: 0), in: text) {
                    let keyword = String(text[keywordRange])
                    if !keywords.contains(keyword) {
                        keywords.append(keyword)
                    }
                }
            }
        }
        
        return keywords
    }
}

// MARK: - 消息气泡
struct MessageBubble: View {
    let message: AIChatMessage
    var onRouteTap: ((AIRouteRecommend) -> Void)? = nil
    
    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if message.isUser {
                Spacer()
                Text(message.content)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(16)
            } else {
                // AI 头像
                Image(systemName: "sparkles")
                    .font(.system(size: 20))
                    .foregroundColor(.white)
                    .frame(width: 32, height: 32)
                    .background(
                        LinearGradient(
                            colors: [Color.purple, Color.blue],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .cornerRadius(16)
                
                VStack(alignment: .leading, spacing: 8) {
                    if message.isStreaming {
                        // 流式传输时显示原始文本
                        Text(message.content)
                            .padding()
                            .background(Color(.systemGray5))
                            .cornerRadius(16)
                        
                        HStack(spacing: 4) {
                            ProgressView()
                                .scaleEffect(0.7)
                            Text("思考中...")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    } else {
                        // 完成后显示清理后的文本
                        if !message.content.isEmpty {
                            Text(simpleFormat(message.content))
                                .padding()
                                .background(Color(.systemGray5))
                                .cornerRadius(16)
                        }
                        
                        // 显示推荐路线卡片
                        if !message.recommendedRoutes.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(message.recommendedRoutes) { route in
                                    RouteRecommendCard(route: route) {
                                        onRouteTap?(route)
                                    }
                                }
                            }
                        }
                    }
                }
                Spacer()
            }
        }
    }
    
    // 简单格式化：移除 Markdown 标记
    private func simpleFormat(_ text: String) -> String {
        var result = text
        result = result.replacingOccurrences(of: "**", with: "")
        result = result.replacingOccurrences(of: "##", with: "")
        result = result.replacingOccurrences(of: "#", with: "")
        result = result.replacingOccurrences(of: "---", with: "")
        result = result.replacingOccurrences(of: "|", with: " ")
        return result
    }
}

// MARK: - 路线推荐卡片
struct RouteRecommendCard: View {
    let route: AIRouteRecommend
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                // 图标
                Image(systemName: "map")
                    .font(.title2)
                    .foregroundColor(.blue)
                    .frame(width: 44, height: 44)
                    .background(Color.blue.opacity(0.1))
                    .cornerRadius(8)
                
                // 信息
                VStack(alignment: .leading, spacing: 4) {
                    Text(route.name)
                        .font(.headline)
                        .foregroundColor(.primary)
                        .lineLimit(1)
                    
                    HStack(spacing: 8) {
                        if let distance = route.distance {
                            Label("\(String(format: "%.1f", distance / 1000)) km", systemImage: "figure.walk")
                        }
                        if let city = route.city {
                            Label(city, systemImage: "location.fill")
                        }
                        if let difficulty = route.difficulty {
                            DifficultyBadge(difficulty: difficulty)
                        }
                    }
                    .font(.caption)
                    .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Image(systemName: "chevron.right")
                    .foregroundColor(.gray)
            }
            .padding(12)
            .background(Color(.systemBackground))
            .cornerRadius(12)
            .shadow(color: Color.black.opacity(0.05), radius: 2, x: 0, y: 1)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - 难度徽章
struct DifficultyBadge: View {
    let difficulty: String
    
    var color: Color {
        switch difficulty.lowercased() {
        case "easy": return .green
        case "medium": return .orange
        case "hard": return .red
        default: return .gray
        }
    }
    
    var displayName: String {
        switch difficulty.lowercased() {
        case "easy": return "简单"
        case "medium": return "中等"
        case "hard": return "困难"
        default: return difficulty
        }
    }
    
    var body: some View {
        Text(displayName)
            .font(.caption2)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .foregroundColor(color)
            .cornerRadius(4)
    }
}

// MARK: - Markdown 文本视图
struct MarkdownTextView: View {
    let content: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            ForEach(Array(formatContent().enumerated()), id: \.offset) { _, line in
                if line.isHeader {
                    Text(line.text)
                        .font(.headline)
                        .fontWeight(.bold)
                        .foregroundColor(.primary)
                } else {
                    Text(line.text)
                        .font(.body)
                        .foregroundColor(.primary)
                }
            }
        }
    }
    
    // 格式化内容
    private func formatContent() -> [MarkdownLine] {
        var lines: [MarkdownLine] = []
        let rawLines = content.components(separatedBy: "\n")
        
        for rawLine in rawLines {
            var line = rawLine
            
            // 跳过空行
            if line.trimmingCharacters(in: .whitespaces).isEmpty { continue }
            
            // 跳过分隔线
            if line.trimmingCharacters(in: .whitespaces) == "---" { continue }
            
            // 跳过表格分隔行
            if line.contains("|---|") || line.contains("| --- |") { continue }
            
            var isHeader = false
            
            // 处理标题
            if line.hasPrefix("## ") {
                line = String(line.dropFirst(3))
                isHeader = true
            } else if line.hasPrefix("# ") {
                line = String(line.dropFirst(2))
                isHeader = true
            }
            
            // 移除 Markdown 标记
            line = line.replacingOccurrences(of: "**", with: "")
            line = line.replacingOccurrences(of: "*", with: "")
            
            // 处理表格行 - 简单移除 | 符号
            if line.contains("|") {
                line = line.replacingOccurrences(of: "|", with: " ")
                line = line.replacingOccurrences(of: "  ", with: " ")
            }
            
            line = line.trimmingCharacters(in: .whitespaces)
            
            if !line.isEmpty {
                lines.append(MarkdownLine(text: line, isHeader: isHeader))
            }
        }
        
        return lines
    }
}

// Markdown 行模型
struct MarkdownLine {
    let text: String
    var isHeader: Bool = false
}

// MARK: - 路线ID包装类型（用于sheet）
struct RouteIdWrapper: Identifiable {
    let id: String
    init(_ id: String) {
        self.id = id
    }
}

// MARK: - 路线详情 Sheet
struct RouteDetailSheet: View {
    let routeId: String
    @State private var route: Route?
    @State private var isLoading = true
    @Environment(\.dismiss) var dismiss
    
    var body: some View {
        NavigationStack {
            Group {
                if isLoading {
                    ProgressView("加载中...")
                } else if let route = route {
                    RouteDetailView(route: route)
                } else {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        Text("路线不存在")
                            .font(.headline)
                        Button("关闭") {
                            dismiss()
                        }
                        .buttonStyle(.bordered)
                    }
                }
            }
            .navigationTitle("路线详情")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("关闭") {
                        dismiss()
                    }
                }
            }
        }
        .task {
            await loadRoute()
        }
    }
    
    private func loadRoute() async {
        do {
            let loadedRoute = try await APIService.shared.fetchRoute(id: routeId)
            await MainActor.run {
                self.route = loadedRoute
                self.isLoading = false
            }
        } catch {
            NSLog("❌ 加载路线失败: %@", error.localizedDescription)
            await MainActor.run {
                self.isLoading = false
            }
        }
    }
}

// MARK: - 导航准备页
struct NavigationPrepView: View {
    let route: Route
    @Environment(\.dismiss) var dismiss
    @State private var selectedMode: NavigationMode = .walking
    @State private var enableVoice = true
    @State private var powerSavingMode = false
    @State private var showNavigationActive = false
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // 1. 路线信息卡片
                    RouteInfoCard(route: route)
                        .padding(.top)
                    
                    // 2. 交通方式选择
                    VStack(alignment: .leading, spacing: 12) {
                        Text("选择出行方式")
                            .font(.headline)
                        
                        HStack(spacing: 12) {
                            ForEach(NavigationMode.allCases) { mode in
                                ModeButton(
                                    mode: mode,
                                    isSelected: selectedMode == mode
                                ) {
                                    selectedMode = mode
                                    // 震动反馈
                                    let generator = UIImpactFeedbackGenerator(style: .light)
                                    generator.impactOccurred()
                                }
                            }
                        }
                    }
                    .padding(.horizontal)
                    
                    // 3. 地图预览（简化版）
                    VStack(alignment: .leading, spacing: 8) {
                        Text("路线概览")
                            .font(.headline)
                            .padding(.horizontal)
                        
                        MapPreviewMini(route: route)
                            .frame(height: 200)
                            .cornerRadius(12)
                            .padding(.horizontal)
                    }
                    
                    // 4. 导航设置
                    VStack(alignment: .leading, spacing: 12) {
                        Text("导航设置")
                            .font(.headline)
                        
                        Toggle("语音播报", isOn: $enableVoice)
                        Toggle("省电模式", isOn: $powerSavingMode)
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 80)
                }
            }
            .navigationTitle("准备导航")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("取消") {
                        dismiss()
                    }
                }
            }
            .overlay(
                // 底部开始按钮
                VStack {
                    Spacer()
                    Button {
                        startNavigation()
                    } label: {
                        Text("开始导航")
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.blue)
                            .cornerRadius(12)
                    }
                    .padding()
                    .background(.ultraThinMaterial)
                }
            )
            .fullScreenCover(isPresented: $showNavigationActive) {
                NavigationActiveView(
                    route: route,
                    mode: selectedMode,
                    enableVoice: enableVoice,
                    powerSavingMode: powerSavingMode
                )
            }
        }
    }
    
    private func startNavigation() {
        // 震动反馈
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
        
        // 跳转到导航页面
        showNavigationActive = true
    }
}

// MARK: - 路线信息卡片
struct RouteInfoCard: View {
    let route: Route
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(route.name)
                .font(.title2.bold())
            
            if let description = route.description {
                Text(description)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .lineLimit(2)
            }
            
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
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
        .padding(.horizontal)
    }
    
    private func difficultyColor(_ difficulty: Difficulty) -> Color {
        switch difficulty {
        case .easy: return .green
        case .medium: return .orange
        case .hard: return .red
        }
    }
}

// MARK: - 交通方式按钮
struct ModeButton: View {
    let mode: NavigationMode
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: mode.icon)
                    .font(.title2)
                Text(mode.name)
                    .font(.caption)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(isSelected ? Color.blue : Color(.systemGray6))
            .foregroundColor(isSelected ? .white : .primary)
            .cornerRadius(12)
        }
    }
}

// MARK: - 地图预览（简化版）
struct MapPreviewMini: View {
    let route: Route
    @State private var region: MKCoordinateRegion
    
    init(route: Route) {
        self.route = route
        _region = State(initialValue: MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 22.5, longitude: 114.0),
            span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
        ))
    }
    
    var body: some View {
        Map(coordinateRegion: $region, showsUserLocation: false, annotationItems: annotationItems) { item in
            MapMarker(coordinate: item.coordinate, tint: item.color)
        }
        .onAppear {
            updateRegion()
        }
    }
    
    private var annotationItems: [MapAnnotationItem] {
        var items: [MapAnnotationItem] = []
        
        guard let points = route.points, !points.isEmpty else { return items }
        let coordinates = CoordinateConverter.wgs84ToGcj02(points.map { $0.location.coordinate })
        
        // 起点
        if let start = coordinates.first {
            items.append(MapAnnotationItem(coordinate: start, color: .green))
        }
        
        // 终点
        if let end = coordinates.last {
            items.append(MapAnnotationItem(coordinate: end, color: .red))
        }
        
        return items
    }
    
    private func updateRegion() {
        guard let points = route.points, !points.isEmpty else { return }
        let coordinates = CoordinateConverter.wgs84ToGcj02(points.map { $0.location.coordinate })
        
        let lats = coordinates.map { $0.latitude }
        let lons = coordinates.map { $0.longitude }
        
        let minLat = lats.min() ?? 0
        let maxLat = lats.max() ?? 0
        let minLon = lons.min() ?? 0
        let maxLon = lons.max() ?? 0
        
        region = MKCoordinateRegion(
            center: CLLocationCoordinate2D(
                latitude: (minLat + maxLat) / 2,
                longitude: (minLon + maxLon) / 2
            ),
            span: MKCoordinateSpan(
                latitudeDelta: max((maxLat - minLat) * 1.3, 0.01),
                longitudeDelta: max((maxLon - minLon) * 1.3, 0.01)
            )
        )
    }
}

// MARK: - 地图标注项
struct MapAnnotationItem: Identifiable {
    let id = UUID()
    let coordinate: CLLocationCoordinate2D
    let color: Color
}

// MARK: - 导航模式
enum NavigationMode: String, CaseIterable, Identifiable {
    case walking
    case running
    case cycling
    
    var id: String { rawValue }
    
    var name: String {
        switch self {
        case .walking: return "步行"
        case .running: return "跑步"
        case .cycling: return "骑行"
        }
    }
    
    var icon: String {
        switch self {
        case .walking: return "figure.walk"
        case .running: return "figure.run"
        case .cycling: return "bicycle"
        }
    }
}

// MARK: - 导航中界面
struct NavigationActiveView: View {
    let route: Route
    let mode: NavigationMode
    let enableVoice: Bool
    let powerSavingMode: Bool
    
    @Environment(\.dismiss) var dismiss
    @StateObject private var navigationService: AMapNavigationService
    @State private var showEndConfirmation = false
    @State private var showOverview = false
    
    init(route: Route, mode: NavigationMode, enableVoice: Bool, powerSavingMode: Bool) {
        self.route = route
        self.mode = mode
        self.enableVoice = enableVoice
        self.powerSavingMode = powerSavingMode
        
        _navigationService = StateObject(wrappedValue: AMapNavigationService(
            route: route,
            mode: mode,
            enableVoice: enableVoice,
            powerSavingMode: powerSavingMode
        ))
    }
    
    var body: some View {
        ZStack(alignment: .top) {
            // 全屏地图
            if navigationService.routeCoordinates.count >= 2 {
                NavigationMapWrapper(
                    routeCoordinates: navigationService.routeCoordinates,
                    currentLocation: navigationService.currentLocation,
                    currentHeading: navigationService.currentHeading,
                    currentSegmentIndex: navigationService.currentSegmentIndex,
                    isOffRoute: navigationService.isOffRoute,
                    showOverview: showOverview
                )
                .ignoresSafeArea()
            } else {
                Color(UIColor.systemGray6)
                    .ignoresSafeArea()
                    .overlay(
                        VStack(spacing: 16) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.system(size: 48))
                                .foregroundColor(.orange)
                            Text("路线数据不完整")
                                .font(.title2.bold())
                            Text("该路线没有轨迹点数据，无法导航")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                            Button("返回") { dismiss() }
                                .buttonStyle(.bordered)
                        }
                    )
            }
            
            // 顶部转向指引横幅
            VStack(spacing: 0) {
                turnBannerView
                    .padding(.top, 50)
                
                // 偏离路线警告
                if navigationService.isOffRoute {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.white)
                        Text("您已偏离路线，请返回")
                            .font(.subheadline.bold())
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(Color.orange)
                    .cornerRadius(20)
                    .padding(.top, 8)
                }
                
                Spacer()
            }
            
            // 底部导航信息面板
            VStack(spacing: 0) {
                Spacer()
                
                bottomPanel
            }
        }
        .navigationBarBackButtonHidden()
        .statusBarHidden(true)
        .confirmationDialog("确认结束导航?", isPresented: $showEndConfirmation) {
            Button("结束导航", role: .destructive) { navigationService.stopNavigation(); dismiss() }
            Button("取消", role: .cancel) {}
        } message: { Text("导航进度将被清空") }
        .alert("到达目的地", isPresented: $navigationService.showArrivalAlert) {
            Button("结束导航") { navigationService.stopNavigation(); dismiss() }
            Button("继续", role: .cancel) {}
        } message: { Text("恭喜您完成本次导航！") }
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                if navigationService.routeCoordinates.count >= 2 {
                    navigationService.startNavigation()
                }
            }
        }
        .onDisappear {
            navigationService.stopNavigation()
        }
    }
    
    // MARK: - 转向横幅
    private var turnBannerView: some View {
        HStack(spacing: 14) {
            if let turn = navigationService.nextTurn {
                // 转向图标
                Image(systemName: turn.icon)
                    .font(.system(size: 30, weight: .bold))
                    .foregroundColor(.white)
                    .frame(width: 52, height: 52)
                    .background(Color(red: 0.13, green: 0.59, blue: 0.95))
                    .cornerRadius(10)
                
                VStack(alignment: .leading, spacing: 3) {
                    Text("前方 \(Int(turn.distance)) 米\(turn.direction)")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)
                    if let road = turn.roadName {
                        Text(road)
                            .font(.system(size: 14))
                            .foregroundColor(.white.opacity(0.85))
                    }
                }
            } else {
                // 无转向时显示沿路线前行
                Image(systemName: "arrow.up")
                    .font(.system(size: 30, weight: .bold))
                    .foregroundColor(.white)
                    .frame(width: 52, height: 52)
                    .background(Color(red: 0.13, green: 0.59, blue: 0.95))
                    .cornerRadius(10)
                
                VStack(alignment: .leading, spacing: 3) {
                    Text("沿路线前行")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)
                    Text(navigationService.remainingDistanceText)
                        .font(.system(size: 14))
                        .foregroundColor(.white.opacity(0.85))
                }
            }
            
            Spacer()
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(Color(red: 0.10, green: 0.16, blue: 0.25))
        .cornerRadius(14)
        .padding(.horizontal, 12)
        .shadow(color: .black.opacity(0.3), radius: 8, y: 4)
    }
    
    // MARK: - 底部导航面板
    private var bottomPanel: some View {
        VStack(spacing: 0) {
            // 进度条
            VStack(spacing: 6) {
                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color.white.opacity(0.2))
                            .frame(height: 6)
                        RoundedRectangle(cornerRadius: 4)
                            .fill(LinearGradient(
                                colors: [Color(red: 0.13, green: 0.59, blue: 0.95), Color(red: 0.25, green: 0.80, blue: 0.50)],
                                startPoint: .leading,
                                endPoint: .trailing
                            ))
                            .frame(width: max(0, geometry.size.width * navigationService.navigationProgress), height: 6)
                    }
                }
                .frame(height: 6)
                
                HStack {
                    Text("已行进 \(Int(navigationService.navigationProgress * 100))%")
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.7))
                    Spacer()
                    Text("剩余 \(navigationService.remainingDistanceText)")
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.7))
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 16)
            
            // 核心数据行
            HStack(spacing: 0) {
                // 剩余距离
                VStack(spacing: 4) {
                    Text(navigationService.remainingDistanceText)
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text("剩余距离")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.6))
                }
                .frame(maxWidth: .infinity)
                
                // 分隔线
                Rectangle()
                    .fill(Color.white.opacity(0.2))
                    .frame(width: 1, height: 40)
                
                // 预计时间
                VStack(spacing: 4) {
                    Text(navigationService.estimatedTimeText)
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text("预计时间")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.6))
                }
                .frame(maxWidth: .infinity)
                
                // 分隔线
                Rectangle()
                    .fill(Color.white.opacity(0.2))
                    .frame(width: 1, height: 40)
                
                // 当前速度
                VStack(spacing: 4) {
                    Text(navigationService.currentSpeedText)
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text("当前速度")
                        .font(.system(size: 11))
                        .foregroundColor(.white.opacity(0.6))
                }
                .frame(maxWidth: .infinity)
            }
            .padding(.vertical, 16)
            
            // 控制按钮行
            HStack(spacing: 0) {
                // 暂停/继续
                Button { navigationService.togglePause() } label: {
                    VStack(spacing: 3) {
                        Image(systemName: navigationService.isPaused ? "play.fill" : "pause.fill")
                            .font(.system(size: 22))
                        Text(navigationService.isPaused ? "继续" : "暂停")
                            .font(.system(size: 11))
                    }
                    .foregroundColor(.white)
                    .frame(width: 64, height: 56)
                    .background(Color.white.opacity(0.15))
                    .cornerRadius(12)
                }
                
                Spacer()
                
                // 结束导航
                Button { showEndConfirmation = true } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "xmark")
                            .font(.system(size: 14, weight: .bold))
                        Text("结束导航")
                            .font(.system(size: 16, weight: .semibold))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 28)
                    .padding(.vertical, 14)
                    .background(Color.red)
                    .cornerRadius(25)
                }
                
                Spacer()
                
                // 全程预览
                Button { showOverview.toggle() } label: {
                    VStack(spacing: 3) {
                        Image(systemName: showOverview ? "location.north.fill" : "map.fill")
                            .font(.system(size: 22))
                        Text(showOverview ? "跟随" : "全程")
                            .font(.system(size: 11))
                    }
                    .foregroundColor(.white)
                    .frame(width: 64, height: 56)
                    .background(Color.white.opacity(0.15))
                    .cornerRadius(12)
                }
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 24)
        }
        .background(
            Color(red: 0.10, green: 0.16, blue: 0.25)
                .ignoresSafeArea()
        )
    }
}

// MARK: - 信息卡片
struct InfoCard: View {
    let title: String
    let value: String
    let icon: String
    
    var body: some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.orange)
            
            Text(value)
                .font(.headline)
                .foregroundColor(.primary)
            
            Text(title)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

// MARK: - 预览
#Preview {
    ExploreView()
}

// MARK: - 高德地图导航服务
class AMapNavigationService: NSObject, ObservableObject {
    private lazy var locationManager: AMapLocationManager = {
        print("🔥 Creating AMapLocationManager...")
        let mgr = AMapLocationManager()
        print("🔥 AMapLocationManager created OK")
        return mgr
    }()
    // 独立的 CLLocationManager 用于获取罗盘 heading（静止也能响应手机朝向）
    private let headingManager = CLLocationManager()
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
        
        print("🔥 AMapNavigationService.init START")
        print("🔥 route.name: \(route.name)")
        print("🔥 route.points count: \(route.points?.count ?? 0)")
        print("🔥 route.distance: \(route.distance)")
        
        // 设置高德隐私合规（必须在使用定位前设置）
        AMapLocationManager.updatePrivacyShow(.didShow, privacyInfo: .didContain)
        AMapLocationManager.updatePrivacyAgree(.didAgree)
        
        if let points = route.points, !points.isEmpty {
            print("🔥 Converting \(points.count) points to GCJ02...")
            // 先过滤掉无效坐标
            let allCoords = points.map { $0.location.coordinate }
            let rawCoords = allCoords.filter { coord in
                coord.latitude != 0 && coord.longitude != 0 &&
                !coord.latitude.isNaN && !coord.longitude.isNaN &&
                abs(coord.latitude) <= 90 && abs(coord.longitude) <= 180
            }
            print("🔥 Valid coordinates: \(rawCoords.count)/\(points.count)")
            if rawCoords.count >= 2 {
                print("🔥 First point: lat=\(rawCoords.first?.latitude ?? 0), lon=\(rawCoords.first?.longitude ?? 0)")
                self.routeCoordinates = CoordinateConverter.wgs84ToGcj02(rawCoords)
                // 过滤转换后可能产生的无效坐标
                self.routeCoordinates = self.routeCoordinates.filter { coord in
                    !coord.latitude.isNaN && !coord.longitude.isNaN &&
                    abs(coord.latitude) <= 90 && abs(coord.longitude) <= 180
                }
                if self.routeCoordinates.count >= 2 {
                    self.totalDistance = calculateTotalDistance()
                }
                print("🔥 routeCoordinates count: \(routeCoordinates.count), totalDistance: \(totalDistance)")
            } else {
                print("🔥 WARNING: not enough valid coordinates after filtering!")
            }
        } else {
            print("🔥 WARNING: route.points is nil or empty - navigation will not work properly!")
        }
        
        setupLocationManager()
        
        self.remainingDistanceText = route.formattedDistance
        self.estimatedTimeText = route.formattedDuration
        print("🔥 AMapNavigationService.init DONE")
    }
    
    private func setupLocationManager() {
        locationManager.delegate = self
        
        if powerSavingMode {
            locationManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
            locationManager.locationTimeout = 10
        } else {
            locationManager.desiredAccuracy = kCLLocationAccuracyBestForNavigation
            locationManager.locationTimeout = 2
        }
        
        locationManager.pausesLocationUpdatesAutomatically = false
        locationManager.allowsBackgroundLocationUpdates = true
        
        // 设置独立的 heading 管理器（磁力计，静止也能响应手机朝向）
        headingManager.delegate = self
        headingManager.headingFilter = 2  // 每变化2度更新一次
        headingManager.headingOrientation = .portrait
        headingManager.requestWhenInUseAuthorization()  // 必须请求定位权限才能获取 heading
    }
    
    func startNavigation() {
        locationManager.startUpdatingLocation()
        headingManager.startUpdatingHeading()  // 开始监听磁力计
        startTime = Date()
        
        if enableVoice {
            speak("导航开始，请沿路线前行")
        }
    }
    
    func stopNavigation() {
        locationManager.stopUpdatingLocation()
        headingManager.stopUpdatingHeading()
    }
    
    func togglePause() {
        isPaused.toggle()
        
        if isPaused {
            locationManager.stopUpdatingLocation()
            headingManager.stopUpdatingHeading()
            speak("导航已暂停")
        } else {
            locationManager.startUpdatingLocation()
            headingManager.startUpdatingHeading()
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
        
        isOffRoute = minDistance > 50
        
        if isOffRoute {
            let now = Date()
            if lastOffRouteAnnounceTime == nil || now.timeIntervalSince(lastOffRouteAnnounceTime!) > 30 {
                lastOffRouteAnnounceTime = now
                speak("您已偏离路线，请返回")
            }
        }
        
        currentSegmentIndex = nearestIndex
        
        var remainingDistance: Double = 0
        if nearestIndex < routeCoordinates.count - 1 {
            let nearestCoord = routeCoordinates[nearestIndex]
            remainingDistance += distanceBetween(location.coordinate, nearestCoord)
            
            for i in (nearestIndex + 1)..<routeCoordinates.count {
                remainingDistance += distanceBetween(routeCoordinates[i-1], routeCoordinates[i])
            }
        }
        
        navigationProgress = min(1.0, max(0, 1.0 - remainingDistance / totalDistance))
        
        if remainingDistance < 1000 {
            remainingDistanceText = String(format: "%.0f 米", remainingDistance)
        } else {
            remainingDistanceText = String(format: "%.1f 公里", remainingDistance / 1000)
        }
        
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
        
        let speedKmh = location.speed * 3.6
        if speedKmh >= 0 {
            currentSpeedText = String(format: "%.1f km/h", speedKmh)
        }
        
        currentLocation = location.coordinate
        // currentHeading 由 CLLocationManager 磁力计更新，不再用 location.course
        
        if remainingDistance < 20 && !hasAnnouncedArrival {
            hasAnnouncedArrival = true
            showArrivalAlert = true
            speak("您已到达目的地")
        }
        
        updateTurnInstruction(nearestIndex: nearestIndex)
        
        lastLocation = location
    }
    
    private func updateTurnInstruction(nearestIndex: Int) {
        guard routeCoordinates.count > 10, nearestIndex < routeCoordinates.count - 10 else {
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

extension AMapNavigationService: AMapLocationManagerDelegate {
    func amapLocationManager(_ manager: AMapLocationManager!, didUpdate location: CLLocation!) {
        guard !isPaused, let location = location else { return }
        
        print("📍 GPS update: lat=\(location.coordinate.latitude) lon=\(location.coordinate.longitude) course=\(location.course) speed=\(location.speed)")
        
        DispatchQueue.main.async {
            self.updateNavigationData(location: location)
        }
    }
    
    func amapLocationManager(_ manager: AMapLocationManager!, didFailWithError error: Error!) {
        print("❌ 高德定位失败: \(error?.localizedDescription ?? "未知错误")")
    }
    
    func amapLocationManager(_ manager: AMapLocationManager!, didChange status: CLAuthorizationStatus) {
        if status == .notDetermined {
            headingManager.requestWhenInUseAuthorization()
        }
    }
}

// MARK: - CLLocationManager 磁力计 delegate（静止也能响应手机朝向）
extension AMapNavigationService: CLLocationManagerDelegate {
    func locationManager(_ manager: CLLocationManager, didUpdateHeading newHeading: CLHeading) {
        guard newHeading.headingAccuracy >= 0 else { return }
        
        // 使用真北方向（magneticHeading + 磁偏 = trueHeading）
        let heading = newHeading.trueHeading > 0 ? newHeading.trueHeading : newHeading.magneticHeading
        print("🧭 heading update: true=\(newHeading.trueHeading) magnetic=\(newHeading.magneticHeading) → using \(heading)")
        
        DispatchQueue.main.async {
            self.currentHeading = heading
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {
        print("🧭 location auth changed: \(status.rawValue)")
        if status == .authorizedWhenInUse || status == .authorizedAlways {
            manager.startUpdatingHeading()
        }
    }
}

// MARK: - 导航地图视图（跟随+旋转模式）
struct NavigationMapWrapper: UIViewRepresentable {
    let routeCoordinates: [CLLocationCoordinate2D]
    let currentLocation: CLLocationCoordinate2D?
    let currentHeading: Double
    let currentSegmentIndex: Int
    let isOffRoute: Bool
    let showOverview: Bool
    
    private var validCoordinates: [CLLocationCoordinate2D] {
        routeCoordinates.filter { coord in
            coord.latitude != 0 && coord.longitude != 0 &&
            !coord.latitude.isNaN && !coord.longitude.isNaN &&
            abs(coord.latitude) <= 90 && abs(coord.longitude) <= 180
        }
    }
    
    func makeUIView(context: Context) -> MKMapView {
        let mapView = MKMapView()
        mapView.delegate = context.coordinator
        mapView.showsUserLocation = false
        mapView.isUserInteractionEnabled = true
        mapView.isPitchEnabled = true
        mapView.isRotateEnabled = true
        mapView.showsCompass = false
        mapView.showsScale = false
        mapView.showsTraffic = true
        mapView.mapType = .standard
        
        let coords = validCoordinates
        if coords.count >= 2 {
            let polyline = MKPolyline(coordinates: coords, count: coords.count)
            polyline.title = "remaining"
            mapView.addOverlay(polyline)
            
            let endAnnotation = MKPointAnnotation()
            endAnnotation.coordinate = coords[coords.count - 1]
            endAnnotation.title = "终点"
            mapView.addAnnotation(endAnnotation)
        }
        
        // 添加导航位置标注
        let locationAnnotation = MKPointAnnotation()
        let initialCoord = coords.first ?? CLLocationCoordinate2D(latitude: 22.5, longitude: 114.0)
        locationAnnotation.coordinate = initialCoord
        locationAnnotation.title = "UserPosition"
        mapView.addAnnotation(locationAnnotation)
        context.coordinator.locationAnnotation = locationAnnotation
        
        context.coordinator.mapView = mapView
        return mapView
    }
    
    func updateUIView(_ mapView: MKMapView, context: Context) {
        let coordinator = context.coordinator
        
        // 更新路线覆盖物
        if coordinator.lastCoordinatesCount != routeCoordinates.count || coordinator.lastSegmentIndex != currentSegmentIndex {
            mapView.removeOverlays(mapView.overlays)
            let coords = validCoordinates
            
            if coords.count >= 2 {
                if currentSegmentIndex > 0 {
                    let completedIdx = min(currentSegmentIndex, coords.count)
                    let completedCoords = Array(coords[0..<completedIdx])
                    if completedCoords.count >= 2 {
                        let completedPolyline = MKPolyline(coordinates: completedCoords, count: completedCoords.count)
                        completedPolyline.title = "completed"
                        mapView.addOverlay(completedPolyline)
                    }
                }
                
                let remainingStart = min(currentSegmentIndex, coords.count - 1)
                let remainingCoords = Array(coords[remainingStart..<coords.count])
                if remainingCoords.count >= 2 {
                    let remainingPolyline = MKPolyline(coordinates: remainingCoords, count: remainingCoords.count)
                    remainingPolyline.title = "remaining"
                    mapView.addOverlay(remainingPolyline)
                }
                
                let existingEnd = mapView.annotations.first { $0.title == "终点" }
                if existingEnd == nil {
                    let endAnnotation = MKPointAnnotation()
                    endAnnotation.coordinate = coords[coords.count - 1]
                    endAnnotation.title = "终点"
                    mapView.addAnnotation(endAnnotation)
                }
            }
            
            coordinator.lastCoordinatesCount = routeCoordinates.count
            coordinator.lastSegmentIndex = currentSegmentIndex
        }
        
        // 更新偏离连线：GPS 位置 → 路线上最近点
        let coords = validCoordinates
        if let location = currentLocation, currentSegmentIndex < coords.count, isOffRoute {
            let nearestCoord = coords[currentSegmentIndex]
            let snapLine = MKPolyline(coordinates: [location, nearestCoord], count: 2)
            snapLine.title = "snapLine"
            // 先移除旧的 snapLine
            let oldSnapLines = mapView.overlays.filter { ($0 as? MKPolyline)?.title == "snapLine" }
            if !oldSnapLines.isEmpty {
                mapView.removeOverlays(oldSnapLines)
            }
            mapView.addOverlay(snapLine)
        } else {
            // 不偏离时移除 snapLine
            let oldSnapLines = mapView.overlays.filter { ($0 as? MKPolyline)?.title == "snapLine" }
            if !oldSnapLines.isEmpty {
                mapView.removeOverlays(oldSnapLines)
            }
        }
        
        // 箭头位置：始终在 GPS 真实位置，偏离路线也在真实位置
        let arrowLocation: CLLocationCoordinate2D
        if let location = currentLocation {
            arrowLocation = location
        } else if currentSegmentIndex < coords.count {
            // 没有 GPS 时 fallback 到路线上的最近点
            arrowLocation = coords[currentSegmentIndex]
        } else if let first = coords.first {
            arrowLocation = first
        } else {
            return
        }
        
        // 相机中心：跟随箭头位置
        let centerLocation = arrowLocation
        
        // 更新位置标注坐标
        if let locationAnnotation = coordinator.locationAnnotation {
            locationAnnotation.coordinate = centerLocation
        }
        
        // 计算航向
        let heading: Double
        if currentHeading > 0 && currentHeading < 360 {
            heading = currentHeading
        } else {
            let lookAhead = min(currentSegmentIndex + 5, coords.count - 1)
            if currentSegmentIndex < coords.count && lookAhead < coords.count && currentSegmentIndex != lookAhead {
                heading = bearing(from: coords[currentSegmentIndex], to: coords[lookAhead])
            } else if coords.count >= 2 {
                heading = bearing(from: coords[0], to: coords[min(5, coords.count - 1)])
            } else {
                heading = 0
            }
        }
        
        if showOverview {
            if coords.count >= 2 {
                let lats = coords.map { $0.latitude }
                let lons = coords.map { $0.longitude }
                if let minLat = lats.min(), let maxLat = lats.max(),
                   let minLon = lons.min(), let maxLon = lons.max() {
                    let span = MKCoordinateSpan(
                        latitudeDelta: (maxLat - minLat) * 1.3 + 0.01,
                        longitudeDelta: (maxLon - minLon) * 1.3 + 0.01
                    )
                    mapView.setRegion(MKCoordinateRegion(
                        center: CLLocationCoordinate2D(latitude: (minLat + maxLat) / 2, longitude: (minLon + maxLon) / 2),
                        span: span
                    ), animated: true)
                }
            }
        } else {
            let camera = MKMapCamera(
                lookingAtCenter: centerLocation,
                fromDistance: 200,
                pitch: 60,
                heading: heading
            )
            mapView.setCamera(camera, animated: true)
        }
        
        // 关键：旋转位置标注，让它始终"指向上方"
        // 地图相机 heading 旋转时，annotation view 也跟着旋转
        // 所以需要反向旋转来补偿：annotation 旋转角 = -heading
        if let annotationView = coordinator.locationAnnotationView {
            let rotationAngle = CGFloat(-heading * .pi / 180)
            UIView.animate(withDuration: 0.3) {
                annotationView.transform = CGAffineTransform(rotationAngle: rotationAngle)
            }
        }
    }
    
    private func bearing(from: CLLocationCoordinate2D, to: CLLocationCoordinate2D) -> Double {
        let lat1 = from.latitude * .pi / 180
        let lon1 = from.longitude * .pi / 180
        let lat2 = to.latitude * .pi / 180
        let lon2 = to.longitude * .pi / 180
        
        let dLon = lon2 - lon1
        let y = sin(dLon) * cos(lat2)
        let x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dLon)
        
        return (atan2(y, x) * 180 / .pi + 360).truncatingRemainder(dividingBy: 360)
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    /// 绘制导航箭头图片：蓝色尖头 + 光晕
    private static func makeNavigationArrowImage() -> UIImage {
        let size = CGSize(width: 60, height: 60)
        let renderer = UIGraphicsImageRenderer(size: size)
        return renderer.image { context in
            let cx = size.width / 2
            let cy = size.height / 2
            
            // 外圈光晕
            let glowColor = UIColor(red: 0.13, green: 0.59, blue: 0.95, alpha: 0.25)
            glowColor.setFill()
            context.cgContext.fillEllipse(in: CGRect(x: 8, y: 8, width: 44, height: 44))
            
            // 蓝色箭头（指向上方）
            let arrowColor = UIColor(red: 0.13, green: 0.59, blue: 0.95, alpha: 1.0)
            arrowColor.setFill()
            
            let path = UIBezierPath()
            // 箭头尖（顶部中心）
            path.move(to: CGPoint(x: cx, y: 4))
            // 右侧
            path.addLine(to: CGPoint(x: cx + 14, y: cy + 8))
            // 右内缩
            path.addLine(to: CGPoint(x: cx + 5, y: cy + 2))
            // 底部右
            path.addLine(to: CGPoint(x: cx + 5, y: cy + 18))
            // 底部左
            path.addLine(to: CGPoint(x: cx - 5, y: cy + 18))
            // 左内缩
            path.addLine(to: CGPoint(x: cx - 5, y: cy + 2))
            // 左侧
            path.addLine(to: CGPoint(x: cx - 14, y: cy + 8))
            path.close()
            
            // 添加阴影
            context.cgContext.setShadow(offset: CGSize(width: 0, height: 2), blur: 4, color: UIColor.black.withAlphaComponent(0.3).cgColor)
            
            path.fill()
            
            // 白色边框高光
            let strokePath = UIBezierPath()
            strokePath.move(to: CGPoint(x: cx, y: 4))
            strokePath.addLine(to: CGPoint(x: cx + 14, y: cy + 8))
            strokePath.addLine(to: CGPoint(x: cx + 5, y: cy + 2))
            strokePath.addLine(to: CGPoint(x: cx + 5, y: cy + 18))
            strokePath.addLine(to: CGPoint(x: cx - 5, y: cy + 18))
            strokePath.addLine(to: CGPoint(x: cx - 5, y: cy + 2))
            strokePath.addLine(to: CGPoint(x: cx - 14, y: cy + 8))
            strokePath.close()
            strokePath.lineWidth = 1.5
            UIColor.white.withAlphaComponent(0.5).setStroke()
            strokePath.stroke()
        }
    }
    
    class Coordinator: NSObject, MKMapViewDelegate {
        weak var mapView: MKMapView?
        var lastCoordinatesCount: Int = -1
        var lastSegmentIndex: Int = -1
        var locationAnnotation: MKPointAnnotation?
        var locationAnnotationView: MKAnnotationView?
        
        func mapView(_ mapView: MKMapView, rendererFor overlay: MKOverlay) -> MKOverlayRenderer {
            if let polyline = overlay as? MKPolyline {
                let renderer = MKPolylineRenderer(polyline: polyline)
                if polyline.title == "completed" {
                    renderer.strokeColor = UIColor.systemGreen.withAlphaComponent(0.8)
                    renderer.lineWidth = 6
                } else if polyline.title == "snapLine" {
                    // 偏离路线时的虚线连接
                    renderer.strokeColor = UIColor.systemOrange.withAlphaComponent(0.7)
                    renderer.lineWidth = 3
                    renderer.lineDashPattern = [6, 4]  // 虚线
                } else {
                    renderer.strokeColor = UIColor(red: 0.13, green: 0.59, blue: 0.95, alpha: 1.0)
                    renderer.lineWidth = 8
                }
                return renderer
            }
            return MKOverlayRenderer(overlay: overlay)
        }
        
        func mapView(_ mapView: MKMapView, viewFor annotation: MKAnnotation) -> MKAnnotationView? {
            if annotation.title == "UserPosition" {
                let identifier = "NavigationUserLocation"
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier)
                
                if annotationView == nil {
                    annotationView = MKAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }
                
                annotationView?.image = NavigationMapWrapper.makeNavigationArrowImage()
                annotationView?.canShowCallout = false
                annotationView?.displayPriority = .required
                annotationView?.centerOffset = CGPoint(x: 0, y: -12)  // 箭头尖对准坐标点
                
                // 保存引用以便后续旋转
                self.locationAnnotationView = annotationView
                
                return annotationView
            }
            
            if annotation.title == "终点" {
                let identifier = "EndPoint"
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier) as? MKMarkerAnnotationView
                
                if annotationView == nil {
                    annotationView = MKMarkerAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }
                
                annotationView?.markerTintColor = .systemRed
                annotationView?.glyphImage = UIImage(systemName: "flag.fill")
                annotationView?.canShowCallout = false
                
                return annotationView
            }
            
            return nil
        }
    }
}

// MARK: - 高德地图导航视图
struct AMapNavigationView: UIViewRepresentable {
    let routeCoordinates: [CLLocationCoordinate2D]
    let currentLocation: CLLocationCoordinate2D?
    let currentHeading: Double
    let currentSegmentIndex: Int
    let isOffRoute: Bool
    
    func makeUIView(context: Context) -> MAMapView {
        print("🔥 AMapNavigationView.makeUIView called, routeCoordinates count: \(routeCoordinates.count)")
        
        // 设置高德地图隐私合规（确保在创建 MAMapView 前设置）
        AMapServices.shared().apiKey = AppConfig.amapAPIKey
        
        let mapView = MAMapView()
        mapView.delegate = context.coordinator
        
        mapView.mapType = .standard
        mapView.isZoomEnabled = true
        mapView.isScrollEnabled = true
        mapView.isRotateEnabled = true
        mapView.showsCompass = true
        mapView.showsScale = true
        // 不使用 MAMapView 内置的用户位置追踪，由我们手动管理
        mapView.showsUserLocation = false
        mapView.userTrackingMode = .none
        
        // 初始绘制路线（仅在坐标数据有效时）
        if routeCoordinates.count >= 2 {
            context.coordinator.updateOverlays(mapView: mapView, routeCoordinates: routeCoordinates, currentSegmentIndex: currentSegmentIndex)
        }
        
        return mapView
    }
    
    func updateUIView(_ mapView: MAMapView, context: Context) {
        let coordinator = context.coordinator
        
        // 路线数据为空时不更新
        guard routeCoordinates.count >= 2 else { return }
        
        // 只在路线数据真正变化时才重建覆盖物
        let needsFullUpdate = coordinator.lastRouteCoordinatesCount != routeCoordinates.count
        let needsProgressUpdate = coordinator.lastSegmentIndex != currentSegmentIndex
        let needsLocationUpdate = !coordinator.isSameLocation(coordinator.lastLocation, currentLocation)
        
        if needsFullUpdate {
            coordinator.updateOverlays(mapView: mapView, routeCoordinates: routeCoordinates, currentSegmentIndex: currentSegmentIndex)
            coordinator.lastRouteCoordinatesCount = routeCoordinates.count
            coordinator.lastSegmentIndex = currentSegmentIndex
        } else if needsProgressUpdate {
            coordinator.updateProgressOverlay(mapView: mapView, routeCoordinates: routeCoordinates, currentSegmentIndex: currentSegmentIndex)
            coordinator.lastSegmentIndex = currentSegmentIndex
        }
        
        // 更新当前位置标注
        if needsLocationUpdate {
            coordinator.updateLocationAnnotation(mapView: mapView, currentLocation: currentLocation, isOffRoute: isOffRoute)
            coordinator.lastLocation = currentLocation
        } else if let location = currentLocation, !isOffRoute {
            mapView.setCenter(location, animated: true)
        }
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator()
    }
    
    class Coordinator: NSObject, MAMapViewDelegate {
        var lastRouteCoordinatesCount: Int = -1
        var lastSegmentIndex: Int = -1
        var lastLocation: CLLocationCoordinate2D?
        
        private let fullRouteOverlayKey = "fullRoute"
        private let completedRouteOverlayKey = "completedRoute"
        
        func isSameLocation(_ a: CLLocationCoordinate2D?, _ b: CLLocationCoordinate2D?) -> Bool {
            guard let a = a, let b = b else {
                return a == nil && b == nil
            }
            return abs(a.latitude - b.latitude) < 0.00001 && abs(a.longitude - b.longitude) < 0.00001
        }
        
        func updateOverlays(mapView: MAMapView, routeCoordinates: [CLLocationCoordinate2D], currentSegmentIndex: Int) {
            mapView.removeOverlays(mapView.overlays)
            mapView.removeAnnotations(mapView.annotations)
            
            guard routeCoordinates.count >= 2 else { return }
            
            // 绘制完整路线（灰色）
            var fullCoords = routeCoordinates
            if let fullPolyline = MAPolyline(coordinates: &fullCoords, count: UInt(routeCoordinates.count)) {
                fullPolyline.title = fullRouteOverlayKey
                mapView.add(fullPolyline)
            }
            
            // 绘制已走过的路线（绿色）
            if currentSegmentIndex > 0 && currentSegmentIndex < routeCoordinates.count {
                var completedCoords = Array(routeCoordinates[0..<currentSegmentIndex])
                if completedCoords.count >= 2, let completedPolyline = MAPolyline(coordinates: &completedCoords, count: UInt(completedCoords.count)) {
                    completedPolyline.title = completedRouteOverlayKey
                    mapView.add(completedPolyline)
                }
            }
            
            // 添加起点标记
            let startAnnotation = MAPointAnnotation()
            startAnnotation.coordinate = routeCoordinates[0]
            startAnnotation.title = "起点"
            mapView.addAnnotation(startAnnotation)
            
            // 添加终点标记
            let endAnnotation = MAPointAnnotation()
            endAnnotation.coordinate = routeCoordinates[routeCoordinates.count - 1]
            endAnnotation.title = "终点"
            mapView.addAnnotation(endAnnotation)
            
            // 仅首次设置地图区域
            if lastRouteCoordinatesCount == -1 {
                let lats = routeCoordinates.map { $0.latitude }
                let lons = routeCoordinates.map { $0.longitude }
                
                let minLat = lats.min() ?? 0
                let maxLat = lats.max() ?? 0
                let minLon = lons.min() ?? 0
                let maxLon = lons.max() ?? 0
                
                let region = MACoordinateRegion(
                    center: CLLocationCoordinate2D(
                        latitude: (minLat + maxLat) / 2,
                        longitude: (minLon + maxLon) / 2
                    ),
                    span: MACoordinateSpan(
                        latitudeDelta: (maxLat - minLat) * 1.3 + 0.01,
                        longitudeDelta: (maxLon - minLon) * 1.3 + 0.01
                    )
                )
                
                mapView.setRegion(region, animated: false)
            }
        }
        
        func updateProgressOverlay(mapView: MAMapView, routeCoordinates: [CLLocationCoordinate2D], currentSegmentIndex: Int) {
            let overlaysToRemove = mapView.overlays.filter { ($0 as? MAPolyline)?.title == completedRouteOverlayKey }
            if !overlaysToRemove.isEmpty {
                mapView.removeOverlays(overlaysToRemove)
            }
            
            if currentSegmentIndex > 0 && currentSegmentIndex < routeCoordinates.count {
                var completedCoords = Array(routeCoordinates[0..<currentSegmentIndex])
                if completedCoords.count >= 2, let completedPolyline = MAPolyline(coordinates: &completedCoords, count: UInt(completedCoords.count)) {
                    completedPolyline.title = completedRouteOverlayKey
                    mapView.add(completedPolyline)
                }
            }
        }
        
        func updateLocationAnnotation(mapView: MAMapView, currentLocation: CLLocationCoordinate2D?, isOffRoute: Bool) {
            let annotationsToRemove = mapView.annotations.filter { $0 is MAUserLocationAnnotation }
            if !annotationsToRemove.isEmpty {
                mapView.removeAnnotations(annotationsToRemove)
            }
            
            if let location = currentLocation {
                let annotation = MAUserLocationAnnotation()
                annotation.coordinate = location
                annotation.title = "当前位置"
                mapView.addAnnotation(annotation)
                
                if !isOffRoute {
                    mapView.setCenter(location, animated: true)
                }
            }
        }
        
        func mapView(_ mapView: MAMapView!, rendererFor overlay: MAOverlay!) -> MAOverlayRenderer! {
            guard let mapView = mapView, let overlay = overlay else { return nil }
            
            if let polyline = overlay as? MAPolyline {
                let renderer = MAPolylineRenderer(overlay: polyline)
                
                if let title = polyline.title, title == completedRouteOverlayKey {
                    renderer?.strokeColor = UIColor.systemGreen
                    renderer?.lineWidth = 5
                } else {
                    renderer?.strokeColor = UIColor.gray.withAlphaComponent(0.5)
                    renderer?.lineWidth = 3
                }
                
                return renderer
            }
            
            return nil
        }
        
        func mapView(_ mapView: MAMapView!, viewFor annotation: MAAnnotation!) -> MAAnnotationView! {
            guard let mapView = mapView, let annotation = annotation else { return nil }
            
            if annotation is MAUserLocationAnnotation {
                let identifier = "UserLocation"
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier)
                
                if annotationView == nil {
                    annotationView = MAAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }
                
                let config = UIImage.SymbolConfiguration(pointSize: 20, weight: .bold)
                let image = UIImage(systemName: "location.north.fill", withConfiguration: config)?
                    .withTintColor(.systemBlue, renderingMode: .alwaysOriginal)
                
                annotationView?.image = image
                annotationView?.centerOffset = .zero
                
                return annotationView
            }
            
            if let title = annotation.title {
                let identifier = "RoutePoint"
                var annotationView = mapView.dequeueReusableAnnotationView(withIdentifier: identifier) as? MAPinAnnotationView
                
                if annotationView == nil {
                    annotationView = MAPinAnnotationView(annotation: annotation, reuseIdentifier: identifier)
                } else {
                    annotationView?.annotation = annotation
                }
                
                if title == "起点" {
                    annotationView?.pinColor = .green
                } else if title == "终点" {
                    annotationView?.pinColor = .red
                }
                
                annotationView?.canShowCallout = true
                
                return annotationView
            }
            
            return nil
        }
    }
}

// 自定义用户位置标注
class MAUserLocationAnnotation: MAPointAnnotation {
    
}
