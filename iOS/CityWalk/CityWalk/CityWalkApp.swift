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
                LoginView()
                    .onChange(of: authVM.isLoggedIn) { _ in }
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
            
            ProfileView(authVM: authVM)
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
        }
    }
}
