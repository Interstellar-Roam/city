import SwiftUI
import UIKit
import PhotosUI
import AMapFoundationKit
import AMapLocationKit

@main
struct CityWalkApp: App {
    @StateObject private var authVM = AuthViewModel()

    init() {
        // 初始化高德地图 SDK
        AMapServices.shared().apiKey = "6a35590781eabd0f2adc39e41c9f6ba1"
        
        // 高德隐私合规（必须在 SDK 使用前设置）
        AMapLocationManager.updatePrivacyShow(.didShow, privacyInfo: .didContain)
        AMapLocationManager.updatePrivacyAgree(.didAgree)
        
        // 设置全局异常处理器
        NSSetUncaughtExceptionHandler { exception in
            let reason = """
            CRASH: \(exception.name.rawValue)
            Reason: \(exception.reason ?? "unknown")
            Stack: \(exception.callStackSymbols.prefix(10).joined(separator: "\n"))
            """
            print("🔥 \(reason)")
            if let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first {
                let file = dir.appendingPathComponent("crash_log.txt")
                try? reason.write(to: file, atomically: true, encoding: .utf8)
            }
        }
    }
    
    var body: some Scene {
        WindowGroup {
            if authVM.isLoggedIn {
                ContentView(authVM: authVM)
            } else {
                LoginView(viewModel: authVM)
            }
        }
    }
}

struct ContentView: View {
    @ObservedObject var authVM: AuthViewModel
    @State private var selectedTab = 0
    
    var body: some View {
        TabView(selection: $selectedTab) {
            ExploreView()
                .tabItem {
                    Image(systemName: "safari")
                    Text("发现")
                }
                .tag(0)
            
            RouteRecordingView()
                .tabItem {
                    Image(systemName: "record.circle")
                    Text("记录")
                }
                .tag(1)
            
            ProfileView(authVM: authVM, selectedTab: $selectedTab)
                .tabItem {
                    Image(systemName: "person")
                    Text("我的")
                }
                .tag(2)
        }
        .tint(.orange)
    }
}

struct ProfileView: View {
    @ObservedObject var authVM: AuthViewModel
    @Binding var selectedTab: Int
    @State private var showEnvPicker = false
    @State private var myRoutes: [Route] = []
    @State private var favoriteRoutes: [Route] = []
    @State private var isLoadingRoutes = false
    @State private var routesErrorMessage: String?
    @State private var actionRoute: Route?
    @State private var showActionSheet = false

    // 用户资料
    @State private var userProfile: UserProfile?
    @State private var showNicknameEditor = false
    @State private var nicknameInput = ""
    @State private var selectedAvatarPhoto: PhotosPickerItem?
    @State private var avatarImageData: Data?

    private let envManager = EnvironmentManager.shared

    var body: some View {
        NavigationView {
            List {
                profileHeaderSection
                statsSection
                myRoutesSection
                myFavoritesSection
                envSection
                logoutSection
            }
            .navigationTitle("个人中心")
            .task {
                await loadAll()
            }
            .refreshable {
                UIImpactFeedbackGenerator(style: .light).impactOccurred()
                await loadAll()
            }
            .alert("设置昵称", isPresented: $showNicknameEditor) {
                TextField("昵称（最多20字）", text: $nicknameInput)
                Button("确定") { Task { await saveNickname() } }
                Button("取消", role: .cancel) {}
            }
            .confirmationDialog("切换环境", isPresented: $showEnvPicker, titleVisibility: .visible, actions: switchEnvActions) {
                Text("切换后将自动退出登录。当前: \(envManager.current.displayName)")
            }
            .confirmationDialog("路线操作", isPresented: $showActionSheet, presenting: actionRoute, actions: routeActionButtons) { actionMessage($0) }
            .onChange(of: selectedAvatarPhoto) { _ in handleAvatarChange() }
        }
    }

    // MARK: - 默认头像
    private var defaultAvatar: some View {
        ZStack {
            Circle().fill(Color.orange.opacity(0.15))
            Image(systemName: "person.fill")
                .font(.title2)
                .foregroundColor(.orange)
        }
    }

    // MARK: - Section Views
    private var profileHeaderSection: some View {
        Section {
            HStack(spacing: 16) {
                PhotosPicker(selection: $selectedAvatarPhoto, matching: .images) {
                    avatarView
                        .frame(width: 56, height: 56)
                        .clipShape(Circle())
                        .overlay(Circle().stroke(Color.orange.opacity(0.3), lineWidth: 2))
                        .overlay(alignment: .bottomTrailing) {
                            Image(systemName: "camera.fill")
                                .font(.system(size: 10)).foregroundColor(.white)
                                .padding(4).background(Circle().fill(Color.orange))
                                .offset(x: 2, y: 2)
                        }
                }
                VStack(alignment: .leading, spacing: 4) {
                    Button {
                        nicknameInput = userProfile?.nickname ?? ""
                        showNicknameEditor = true
                    } label: {
                        HStack(spacing: 4) {
                            Text(userProfile?.displayName ?? TokenStorage.shared.getPhone() ?? "未登录")
                                .font(.headline).foregroundColor(.primary)
                            Image(systemName: "pencil").font(.caption2).foregroundColor(.secondary)
                        }
                    }
                    if let phone = userProfile?.phone, !phone.isEmpty {
                        Text(phone).font(.caption).foregroundColor(.secondary)
                    }
                }
            }
            .padding(.vertical, 8)
        }
    }

    private var avatarView: some View {
        Group {
            if let avatarURL = userProfile?.avatar, let url = URL(string: avatarURL) {
                AsyncImage(url: url) { phase in
                    if case .success(let image) = phase {
                        image.resizable().scaledToFill()
                    } else {
                        defaultAvatar
                    }
                }
            } else {
                defaultAvatar
            }
        }
    }

    private var statsSection: some View {
        Section {
            HStack(spacing: 12) {
                StatCard(icon: "figure.walk", value: userProfile?.stats.formattedDistance ?? "--", label: "总里程", color: .orange)
                StatCard(icon: "map", value: "\(userProfile?.stats.routeCount ?? 0)", label: "路线", color: .blue)
                StatCard(icon: "heart.fill", value: "\(userProfile?.stats.favoriteCount ?? 0)", label: "收藏", color: .red)
            }
            .padding(.vertical, 4)
        }
    }

    private var myRoutesSection: some View {
        Section {
            if isLoadingRoutes {
                HStack { Spacer(); ProgressView(); Spacer() }
            } else if let error = routesErrorMessage {
                Text(error).foregroundColor(.secondary).font(.subheadline)
            } else if myRoutes.isEmpty {
                EmptyStateView(icon: "map", title: "还没有记录过路线", subtitle: "走出去，探索你的城市", actionTitle: "去记录第一条路线", onAction: { selectedTab = 1 })
            } else {
                ForEach(Array(myRoutes.prefix(3))) { route in
                    NavigationLink(destination: RouteDetailView(route: route)) {
                        MyRouteRow(route: route)
                    }
                    .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                        Button(role: .destructive) {
                            actionRoute = route; showActionSheet = true
                        } label: { Label("删除", systemImage: "trash") }
                    }
                }
                if myRoutes.count > 3 {
                    NavigationLink(destination: AllRoutesView(routes: myRoutes)) {
                        HStack { Text("查看全部路线"); Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundColor(.secondary) }
                    }
                }
            }
        } header: {
            routesSectionHeader
        }
    }

    private var myFavoritesSection: some View {
        Section {
            if favoriteRoutes.isEmpty {
                HStack { Text("暂无收藏").foregroundColor(.secondary).font(.subheadline); Spacer() }
            } else {
                ForEach(Array(favoriteRoutes.prefix(3))) { route in
                    NavigationLink(destination: RouteDetailView(route: route)) {
                        MyRouteRow(route: route)
                    }
                }
                if favoriteRoutes.count > 3 {
                    NavigationLink(destination: AllRoutesView(routes: favoriteRoutes, title: "我的收藏")) {
                        HStack { Text("查看全部收藏"); Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundColor(.secondary) }
                    }
                }
            }
        } header: {
            favoritesSectionHeader
        }
    }

    private var envSection: some View {
        Section {
            HStack {
                Text("当前环境"); Spacer()
                Text(envManager.current.displayName)
                    .foregroundColor(envManager.current == .production ? .green : .orange)
                Image(systemName: "chevron.right").font(.caption).foregroundColor(.secondary)
            }
            .contentShape(Rectangle())
            .onTapGesture {
                UIImpactFeedbackGenerator(style: .light).impactOccurred()
                showEnvPicker = true
            }
        }
    }

    private var logoutSection: some View {
        Section {
            Button(role: .destructive) {
                UIImpactFeedbackGenerator(style: .medium).impactOccurred()
                Task { await authVM.logout() }
            } label: {
                HStack { Spacer(); Text("退出登录"); Spacer() }
            }
        }
    }

    // MARK: - Section Headers
    private var routesSectionHeader: some View {
        HStack {
            Text("我的路线")
            Spacer()
            Text("\(myRoutes.count) 条")
                .foregroundColor(.secondary)
                .font(.subheadline)
        }
    }

    private var favoritesSectionHeader: some View {
        HStack {
            Text("我的收藏")
            Spacer()
            Text("\(favoriteRoutes.count) 条")
                .foregroundColor(.secondary)
                .font(.subheadline)
        }
    }

    // MARK: - Helpers
    @ViewBuilder
    private func routeActionButtons(_ route: Route) -> some View {
        Button("设为私密", role: .none) { Task { await setRoutePrivate(route) } }
        Button("删除路线", role: .destructive) {
            UIImpactFeedbackGenerator(style: .heavy).impactOccurred()
            Task { await deleteMyRoute(route) }
        }
        Button("取消", role: .cancel) {}
    }

    @ViewBuilder
    private func switchEnvActions() -> some View {
        ForEach(EnvironmentManager.Environment.allCases, id: \.self) { env in
            Button(env.displayName) {
                envManager.switchTo(env)
                authVM.isLoggedIn = false
            }
        }
        Button("取消", role: .cancel) {}
    }

    private func actionMessage(_ route: Route) -> Text {
        Text("\"\(route.name)\" — 删除后将无法恢复。您也可以选择设为私密，仅自己可见。")
    }

    private func handleAvatarChange() {
        Task {
            if let data = try? await selectedAvatarPhoto?.loadTransferable(type: Data.self) {
                avatarImageData = data
                await uploadAvatar()
            }
        }
    }

    // MARK: - 数据加载
    private func loadAll() async {
        isLoadingRoutes = true
        routesErrorMessage = nil
        do {
            async let routes = APIService.shared.fetchMyRoutes()
            async let favs = APIService.shared.fetchFavorites()
            async let profile = APIService.shared.fetchUserProfile()

            let (routeResult, favResult, profileResult) = try await (routes, favs, profile)
            myRoutes = routeResult.items
            favoriteRoutes = favResult.items
            userProfile = profileResult
        } catch {
            routesErrorMessage = error.localizedDescription
        }
        isLoadingRoutes = false
    }

    private func deleteMyRoute(_ route: Route) async {
        do {
            try await APIService.shared.deleteRoute(id: route.id)
            myRoutes.removeAll { $0.id == route.id }
        } catch {
            routesErrorMessage = error.localizedDescription
        }
    }

    private func setRoutePrivate(_ route: Route) async {
        do {
            try await APIService.shared.updateRoute(id: route.id, name: nil, description: nil, difficulty: nil, tags: nil, city: nil, isPublished: false)
            await loadAll()
        } catch {
            routesErrorMessage = error.localizedDescription
        }
    }

    // MARK: - 昵称保存
    private func saveNickname() async {
        let trimmed = nicknameInput.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }
        do {
            _ = try await APIService.shared.updateUserProfile(nickname: trimmed)
            await loadAll()
        } catch {
            routesErrorMessage = error.localizedDescription
        }
    }

    // MARK: - 头像上传
    private func uploadAvatar() async {
        guard let imgData = avatarImageData else { return }
        do {
            let optimized = optimizeImage(imgData)
            let url = try await APIService.shared.uploadImage(imageData: optimized)
            _ = try await APIService.shared.updateUserProfile(avatar: url)
            await loadAll()
        } catch {
            routesErrorMessage = error.localizedDescription
        }
    }

    private func optimizeImage(_ data: Data, targetKB: Int = 200) -> Data {
        guard let image = UIImage(data: data) else { return data }
        let maxDim: CGFloat = 600
        let scale = min(maxDim / image.size.width, maxDim / image.size.height, 1.0)
        let resized: UIImage
        if scale < 1.0 {
            let newSize = CGSize(width: image.size.width * scale, height: image.size.height * scale)
            let renderer = UIGraphicsImageRenderer(size: newSize)
            resized = renderer.image { _ in image.draw(in: CGRect(origin: .zero, size: newSize)) }
        } else { resized = image }
        var low: CGFloat = 0.0, high: CGFloat = 1.0
        var best = resized.jpegData(compressionQuality: 1.0) ?? data
        for _ in 0..<8 {
            let mid = (low + high) / 2
            guard let d = resized.jpegData(compressionQuality: mid) else { break }
            if d.count <= targetKB * 1024 { best = d; high = mid } else { low = mid }
        }
        return best
    }
}

// MARK: - 统计卡片
struct StatCard: View {
    let icon: String
    let value: String
    let label: String
    let color: Color

    var body: some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(color)
            Text(value)
                .font(.system(.title3, design: .rounded))
                .fontWeight(.bold)
                .foregroundColor(.primary)
            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(color.opacity(0.08))
        )
    }
}

// MARK: - 路线行
struct MyRouteRow: View {
    let route: Route

    private let thumbWidth: CGFloat = 44

    var body: some View {
        HStack(spacing: 12) {
            // 封面缩略图
            if let coverURL = route.coverImage, let url = URL(string: coverURL) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().scaledToFill()
                            .frame(width: thumbWidth, height: thumbWidth)
                            .cornerRadius(8).clipped()
                    default:
                        thumbnailPlaceholder
                    }
                }
            } else {
                thumbnailPlaceholder
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(route.name)
                    .font(.headline)
                    .lineLimit(1)

                HStack(spacing: 12) {
                    Label(route.formattedDistance, systemImage: "point.topleft.down.to.point.bottomright.curvepath")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    if let duration = route.duration {
                        Label(route.formattedDuration, systemImage: "clock")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }

                    if let difficulty = route.difficulty {
                        Label(difficulty.displayText, systemImage: difficulty.icon)
                            .font(.subheadline)
                            .foregroundColor(difficulty.color == "green" ? .green : difficulty.color == "orange" ? .orange : .red)
                    }
                }

                if let city = route.city {
                    Text(city)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var thumbnailPlaceholder: some View {
        RoundedRectangle(cornerRadius: 8)
            .fill(Color(.systemGray5))
            .frame(width: thumbWidth, height: thumbWidth)
            .overlay(
                Image(systemName: "mountain.2.fill")
                    .font(.caption)
                    .foregroundColor(.secondary.opacity(0.5))
            )
    }
}

// MARK: - 全部路线列表
struct AllRoutesView: View {
    let routes: [Route]
    let title: String
    @State private var actionRoute: Route?
    @State private var showActionSheet = false
    @State private var currentRoutes: [Route]

    init(routes: [Route], title: String = "我的路线") {
        self.routes = routes
        self.title = title
        _currentRoutes = State(initialValue: routes)
    }

    private struct GroupedRoutes {
        let title: String
        let routes: [Route]
    }

    private var groupedRoutes: [GroupedRoutes] {
        let calendar = Calendar.current
        let today = Date()

        var todayRoutes: [Route] = []
        var weekRoutes: [Route] = []
        var olderRoutes: [Route] = []

        for route in currentRoutes {
            guard let date = route.createdAt else {
                olderRoutes.append(route)
                continue
            }
            if calendar.isDateInToday(date) {
                todayRoutes.append(route)
            } else if calendar.isDate(date, equalTo: today, toGranularity: .weekOfYear) {
                weekRoutes.append(route)
            } else {
                olderRoutes.append(route)
            }
        }

        var result: [GroupedRoutes] = []
        if !todayRoutes.isEmpty { result.append(GroupedRoutes(title: "今天", routes: todayRoutes)) }
        if !weekRoutes.isEmpty { result.append(GroupedRoutes(title: "本周", routes: weekRoutes)) }
        if !olderRoutes.isEmpty { result.append(GroupedRoutes(title: "更早", routes: olderRoutes)) }
        return result
    }

    var body: some View {
        List {
            ForEach(groupedRoutes, id: \.title) { group in
                Section(group.title) {
                    ForEach(group.routes) { route in
                        NavigationLink(destination: RouteDetailView(route: route)) {
                            HStack(spacing: 12) {
                                // 缩略图
                                if let coverURL = route.coverImage, let url = URL(string: coverURL) {
                                    AsyncImage(url: url) { phase in
                                        if case .success(let image) = phase {
                                            image.resizable().scaledToFill()
                                                .frame(width: 40, height: 40)
                                                .cornerRadius(6).clipped()
                                        }
                                    }
                                }

                                VStack(alignment: .leading, spacing: 4) {
                                    Text(route.name)
                                        .font(.headline)
                                        .lineLimit(1)
                                    HStack(spacing: 8) {
                                        Text(route.formattedDistance)
                                            .font(.subheadline)
                                            .foregroundColor(.secondary)
                                        if let diff = route.difficulty {
                                            Text(diff.displayText)
                                                .font(.caption)
                                                .foregroundColor(diff.color == "green" ? .green : diff.color == "orange" ? .orange : .red)
                                        }
                                        if let date = route.createdAt {
                                            Text(formatDate(date))
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                        }
                                    }
                                }
                            }
                            .padding(.vertical, 2)
                        }
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button(role: .destructive) {
                                actionRoute = route
                                showActionSheet = true
                            } label: {
                                Label("删除", systemImage: "trash")
                            }
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .confirmationDialog("路线操作", isPresented: $showActionSheet, presenting: actionRoute) { route in
            Button("设为私密", role: .none) {
                Task {
                    try? await APIService.shared.updateRoute(id: route.id, name: nil, description: nil, difficulty: nil, tags: nil, city: nil, isPublished: false)
                    currentRoutes.removeAll { $0.id == route.id }
                }
            }
            Button("删除路线", role: .destructive) {
                Task {
                    try? await APIService.shared.deleteRoute(id: route.id)
                    currentRoutes.removeAll { $0.id == route.id }
                }
            }
            Button("取消", role: .cancel) {}
        } message: { route in
            Text("\"\(route.name)\" — 删除后将无法恢复。也可以设为私密，仅自己可见。")
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MM-dd HH:mm"
        return formatter.string(from: date)
    }
}
