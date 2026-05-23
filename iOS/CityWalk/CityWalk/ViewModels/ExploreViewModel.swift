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
    
    // 分类标签（与数据库标签对应）
    let categories = ["推荐", "徒步", "跑步", "骑行", "公园", "海边", "越野跑"]
    
    // MARK: - 服务
    private let apiService = APIService.shared
    
    // MARK: - 任务管理
    private var currentTask: Task<Void, Never>?
    private var isLoadedOnce = false  // 是否已加载过一次
    
    // MARK: - 方法
    
    /// 加载所有路线
    func loadRoutes() async {
        // 取消之前的任务
        currentTask?.cancel()
        
        currentTask = Task {
            isLoading = true
            errorMessage = nil
            
            do {
                let fetchedRoutes = try await apiService.fetchRoutes()
                
                // 检查是否被取消
                if Task.isCancelled {
                    isLoading = false
                    return
                }
                
                routes = fetchedRoutes
                isLoadedOnce = true
                
                // 设置精选路线（取前3条或按距离排序）
                featuredRoutes = Array(fetchedRoutes.sorted { $0.distance > $1.distance }.prefix(3))
                
                isLoading = false
            } catch is CancellationError {
                // 请求被取消，不做任何处理
                print("ℹ️ 请求被取消")
                isLoading = false
            } catch {
                // 检查是否被取消
                if Task.isCancelled {
                    isLoading = false
                    return
                }
                
                // 只在没有成功加载过时才显示错误
                if !isLoadedOnce {
                    errorMessage = error.localizedDescription
                }
                isLoading = false
            }
        }
        
        await currentTask?.value
    }
    
    // MARK: - 搜索防抖
    private var searchDebounceTask: Task<Void, Never>?
    
    /// 搜索路线（带 300ms 防抖）
    func searchRoutes() async {
        guard !searchKeyword.isEmpty else {
            searchDebounceTask?.cancel()
            await loadRoutes()
            return
        }
        
        // 取消之前的防抖任务
        searchDebounceTask?.cancel()
        
        // 创建新的防抖任务
        searchDebounceTask = Task {
            // 等待 300ms
            try? await Task.sleep(nanoseconds: 300_000_000)
            
            // 检查是否被取消
            if Task.isCancelled { return }
            
            await performSearch()
        }
    }
    
    /// 执行实际搜索
    private func performSearch() async {
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
            routes = []
            errorMessage = "搜索失败: \(error.localizedDescription)"
            isLoading = false
        }
    }
    
    /// 选择分类
    func selectCategory(_ category: String) {
        selectedCategory = category
        
        Task {
            isLoading = true
            defer { isLoading = false }
            
            do {
                if category == "推荐" {
                    routes = try await apiService.fetchRoutes()
                } else {
                    // 从后端按标签筛选
                    routes = try await apiService.fetchRoutes(tags: [category])
                }
            } catch {
                errorMessage = "加载失败: \(error.localizedDescription)"
            }
        }
    }
    
    /// 刷新数据
    func refresh() async {
        // 重置错误信息
        errorMessage = nil
        await loadRoutes()
    }
}
