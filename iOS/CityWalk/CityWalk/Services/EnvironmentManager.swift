import Foundation

/// 环境管理：正式 / 测试环境切换
class EnvironmentManager {
    static let shared = EnvironmentManager()

    enum Environment: String, CaseIterable {
        case production
        case test

        var displayName: String {
            switch self {
            case .production: return "正式环境"
            case .test: return "测试环境"
            }
        }
    }

    private let envKey = "app.environment"
    private let testHostKey = "app.test_host"

    private let defaults = UserDefaults.standard

    /// 当前环境
    var current: Environment {
        get {
            let raw = defaults.string(forKey: envKey) ?? ""
            return Environment(rawValue: raw) ?? .test
        }
        set {
            defaults.set(newValue.rawValue, forKey: envKey)
        }
    }

    /// 测试环境 Host IP（可自定义）
    var testHost: String {
        get { defaults.string(forKey: testHostKey) ?? "192.168.31.34" }
        set { defaults.set(newValue, forKey: testHostKey) }
    }

    /// 当前 API Base URL
    var apiBaseURL: String {
        switch current {
        case .production:
            return "https://api.moon-alpha.com/api/v1"
        case .test:
            return "http://\(testHost):8000/api/v1"
        }
    }

    /// 切换环境（清除 Token + 保存）
    func switchTo(_ env: Environment) {
        current = env
        TokenStorage.shared.clearAll()
    }
}
