import SwiftUI
import AMapFoundationKit
import AMapLocationKit

@main
struct CityWalkApp: App {
    init() {
        // 初始化高德地图 SDK
        AMapServices.shared().apiKey = "6a35590781eabd0f2adc39e41c9f6ba1"
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
            
            Text("我的路线")
                .tabItem {
                    Image(systemName: "map")
                    Text("路线")
                }
                .tag(1)
            
            Text("个人中心")
                .tabItem {
                    Image(systemName: "person")
                    Text("我的")
                }
                .tag(2)
        }
        .tint(.orange)
    }
}
