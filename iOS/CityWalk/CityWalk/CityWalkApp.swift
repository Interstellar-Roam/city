import SwiftUI
import AMapFoundationKit
import AMapLocationKit

@main
struct CityWalkApp: App {
    init() {
        // 初始化高德地图 SDK
        AMapServices.shared().apiKey = "6a35590781eabd0f2adc39e41c9f6ba1"
        
        // 高德隐私合规（必须在 SDK 使用前设置）
        AMapLocationManager.updatePrivacyShow(.didShow, privacyInfo: .didContain)
        AMapLocationManager.updatePrivacyAgree(.didAgree)
        
        // 设置全局异常处理器来捕获崩溃信息
        NSSetUncaughtExceptionHandler { exception in
            let reason = """
            CRASH: \(exception.name.rawValue)
            Reason: \(exception.reason ?? "unknown")
            Stack: \(exception.callStackSymbols.prefix(10).joined(separator: "\n"))
            """
            print("🔥 \(reason)")
            // 写入文件
            if let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first {
                let file = dir.appendingPathComponent("crash_log.txt")
                try? reason.write(to: file, atomically: true, encoding: .utf8)
            }
        }
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
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
            
            Text("个人中心")
                .font(.title2)
                .foregroundColor(AppTheme.textSecondary)
                .tabItem {
                    Image(systemName: "person")
                    Text("我的")
                }
                .tag(2)
        }
        .tint(AppTheme.accent)
        .preferredColorScheme(.dark)
    }
}
