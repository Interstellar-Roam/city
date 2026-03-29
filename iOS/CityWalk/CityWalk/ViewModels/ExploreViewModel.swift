import Foundation

@MainActor
class ExploreViewModel: ObservableObject {
    // MARK: - 状态
    @Published var routes: [Route] = []
    @Published var featuredRoutes: [Route] = []
    @Published var searchKeyword: String = ""
    @Published var selectedCategory: String = "推荐"
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    
    // 分类标签
    let categories = ["推荐", "徒步", "骑行", "跑步", "风景", "城市", "公园", "海边"]
    
    // MARK: - 服务
    private let apiService = APIService.shared
    
    // MARK: - 方法
    
    /// 加载所有路线
    func loadRoutes() async {
        isLoading = true
        errorMessage = nil
        
        do {
            let fetchedRoutes = try await apiService.fetchRoutes()
            routes = fetchedRoutes
            
            // 设置精选路线（取前3条或按距离排序）
            featuredRoutes = Array(fetchedRoutes.sorted { $0.distance > $1.distance }.prefix(3))
            
            isLoading = false
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }
    
    /// 搜索路线
    func searchRoutes() async {
        guard !searchKeyword.isEmpty else {
            await loadRoutes()
            return
        }
        
        isLoading = true
        errorMessage = nil
        
        print("🔍 开始搜索: \(searchKeyword)")
        
        do {
            let results = try await apiService.searchRoutes(keyword: searchKeyword)
            print("✅ 搜索完成，找到 \(results.count) 条路线")
            routes = results
            isLoading = false
        } catch {
            print("❌ 搜索失败: \(error.localizedDescription)")
            // 搜索失败时清空结果
            routes = []
            errorMessage = "搜索失败: \(error.localizedDescription)"
            isLoading = false
        }
    }
    
    /// 选择分类
    func selectCategory(_ category: String) {
        selectedCategory = category
        
        // 根据分类筛选（这里用标签匹配）
        if category == "推荐" {
            Task {
                await loadRoutes()
            }
        } else {
            routes = routes.filter { route in
                route.tags?.contains { tag in
                    tag.localizedCaseInsensitiveContains(category)
                } ?? false
            }
        }
    }
    
    /// 刷新数据
    func refresh() async {
        await loadRoutes()
    }
}
