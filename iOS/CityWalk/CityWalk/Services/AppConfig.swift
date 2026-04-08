import Foundation

/// 应用全局配置
enum AppConfig {
    // MARK: - 服务器配置
    /// 服务器地址（修改此地址以连接不同的后端服务器）
    /// 开发环境示例：
    /// - 本机模拟器: "localhost"
    /// - 真机测试: "192.168.x.x" (本机IP)
    /// - 生产环境: "api.citywalk.com"
    static let serverHost = "192.168.31.34"
    
    /// 服务器端口
    static let serverPort = 8000
    
    /// API 版本
    static let apiVersion = "v1"
    
    /// 完整的 API Base URL
    static var apiBaseURL: String {
        "http://\(serverHost):\(serverPort)/api/\(apiVersion)"
    }
    
    // MARK: - 高德地图配置
    /// 高德地图 API Key (iOS端)
    static let amapAPIKey = "6a35590781eabd0f2adc39e41c9f6ba1"
    
    // MARK: - 其他配置
    /// 默认用户ID
    static let defaultUserId = "ios_user"
    
    /// 请求超时时间（秒）
    static let requestTimeout: TimeInterval = 30
}
