import SwiftUI
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
    @State private var isLoadingRoutes = false
    @State private var routesErrorMessage: String?
    @State private var actionRoute: Route?
    @State private var showActionSheet = false

    private let envManager = EnvironmentManager.shared

    var body: some View {
        NavigationView {
            List {
                Section {
                    HStack {
                        Image(systemName: "person.circle.fill")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(TokenStorage.shared.getPhone() ?? "未登录")
                                .font(.headline)
                        }
                    }
                    .padding(.vertical, 8)
                }

                // 我的路线
                Section {
                    if isLoadingRoutes {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    } else if let error = routesErrorMessage {
                        Text(error)
                            .foregroundColor(.secondary)
                            .font(.subheadline)
                    } else if myRoutes.isEmpty {
                        EmptyStateView(
                            icon: "map",
                            title: "还没有记录过路线",
                            subtitle: "走出去，探索你的城市",
                            actionTitle: "去记录第一条路线",
                            onAction: { selectedTab = 1 }
                        )
                    } else {
                        ForEach(Array(myRoutes.prefix(3))) { route in
                            NavigationLink(destination: RouteDetailView(route: route)) {
                                MyRouteRow(route: route)
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
                        if myRoutes.count > 3 {
                            NavigationLink(destination: AllRoutesView(routes: myRoutes)) {
                                HStack {
                                    Text("查看全部路线")
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                    }
                } header: {
                    HStack {
                        Text("我的路线")
                        Spacer()
                        Text("\(myRoutes.count) 条")
                            .foregroundColor(.secondary)
                            .font(.subheadline)
                    }
                }

                Section {
                    HStack {
                        Text("当前环境")
                        Spacer()
                        Text(envManager.current.displayName)
                            .foregroundColor(envManager.current == .production ? .green : .orange)
                        Image(systemName: "chevron.right")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .contentShape(Rectangle())
                    .onTapGesture { showEnvPicker = true }
                }

                Section {
                    Button(role: .destructive, action: {
                        Task { await authVM.logout() }
                    }) {
                        HStack {
                            Spacer()
                            Text("退出登录")
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("个人中心")
            .task {
                await loadMyRoutes()
            }
            .refreshable {
                await loadMyRoutes()
            }
            .confirmationDialog("切换环境", isPresented: $showEnvPicker, titleVisibility: .visible) {
                ForEach(EnvironmentManager.Environment.allCases, id: \.self) { env in
                    Button(env.displayName) {
                        envManager.switchTo(env)
                        authVM.isLoggedIn = false
                    }
                }
                Button("取消", role: .cancel) {}
            } message: {
                Text("切换后将自动退出登录。当前: \(envManager.current.displayName)")
            }
            .confirmationDialog("路线操作", isPresented: $showActionSheet, presenting: actionRoute) { route in
                Button("设为私密", role: .none) {
                    Task { await setRoutePrivate(route) }
                }
                Button("删除路线", role: .destructive) {
                    Task { await deleteMyRoute(route) }
                }
                Button("取消", role: .cancel) {}
            } message: { route in
                Text("\"\(route.name)\" — 删除后将无法恢复。您也可以选择设为私密，仅自己可见。")
            }
        }
    }

    private func loadMyRoutes() async {
        isLoadingRoutes = true
        routesErrorMessage = nil
        do {
            let result = try await APIService.shared.fetchMyRoutes()
            myRoutes = result.items
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
            await loadMyRoutes()
        } catch {
            routesErrorMessage = error.localizedDescription
        }
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
    @State private var actionRoute: Route?
    @State private var showActionSheet = false
    @State private var currentRoutes: [Route]

    init(routes: [Route]) {
        self.routes = routes
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
        .navigationTitle("我的路线")
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
