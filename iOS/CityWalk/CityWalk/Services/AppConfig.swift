import Foundation

/// 应用全局配置
enum AppConfig {
    // MARK: - 服务器配置
    /// API Base URL
    static let apiBaseURL = "https://api.moon-alpha.com/api/v1"
    
    // MARK: - 高德地图配置
    /// 高德地图 API Key (iOS端)
    static let amapAPIKey = "6a35590781eabd0f2adc39e41c9f6ba1"
    
    // MARK: - 其他配置
    /// 默认用户ID
    static let defaultUserId = "ios_user"
    
    /// 请求超时时间（秒）
    static let requestTimeout: TimeInterval = 30
}
