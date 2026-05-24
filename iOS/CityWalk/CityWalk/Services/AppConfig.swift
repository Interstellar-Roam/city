import Foundation

/// 应用全局配置
enum AppConfig {
    // MARK: - 服务器配置
    /// API Base URL（动态，根据当前环境返回）
    static var apiBaseURL: String {
        EnvironmentManager.shared.apiBaseURL
    }
    
    // MARK: - 高德地图配置
    /// 高德地图 API Key (iOS端)
    static let amapAPIKey = "6a35590781eabd0f2adc39e41c9f6ba1"
    
    // MARK: - 其他配置
    /// 请求超时时间（秒）
    static let requestTimeout: TimeInterval = 30
}
