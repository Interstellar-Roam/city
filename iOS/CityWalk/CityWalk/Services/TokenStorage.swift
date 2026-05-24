import Foundation

/// Token 持久化存储（UserDefaults）
class TokenStorage {
    static let shared = TokenStorage()

    private let accessTokenKey = "auth.access_token"
    private let refreshTokenKey = "auth.refresh_token"
    private let expiresAtKey = "auth.expires_at"
    private let userPhoneKey = "auth.user_phone"
    private let userIdKey = "auth.user_id"

    private let defaults = UserDefaults.standard

    private init() {}

    // MARK: - 存取

    func saveTokens(access: String, refresh: String, expiresIn: Int, phone: String) {
        defaults.set(access, forKey: accessTokenKey)
        defaults.set(refresh, forKey: refreshTokenKey)
        defaults.set(Date().addingTimeInterval(TimeInterval(expiresIn)), forKey: expiresAtKey)
        defaults.set(phone, forKey: userPhoneKey)
    }

    func getAccessToken() -> String? {
        return defaults.string(forKey: accessTokenKey)
    }

    func getRefreshToken() -> String? {
        return defaults.string(forKey: refreshTokenKey)
    }

    func getPhone() -> String? {
        return defaults.string(forKey: userPhoneKey)
    }

    func saveUserId(_ id: String) {
        defaults.set(id, forKey: userIdKey)
    }

    func getUserId() -> String? {
        return defaults.string(forKey: userIdKey)
    }

    var isLoggedIn: Bool {
        guard let token = getAccessToken(), !token.isEmpty else { return false }
        guard let expires = defaults.object(forKey: expiresAtKey) as? Date else { return false }
        return expires > Date()
    }

    var isExpiringSoon: Bool {
        guard let expires = defaults.object(forKey: expiresAtKey) as? Date else { return true }
        return expires.timeIntervalSinceNow < 120  // 2 分钟内过期视为即将过期
    }

    func clearAll() {
        defaults.removeObject(forKey: accessTokenKey)
        defaults.removeObject(forKey: refreshTokenKey)
        defaults.removeObject(forKey: expiresAtKey)
        defaults.removeObject(forKey: userPhoneKey)
        defaults.removeObject(forKey: userIdKey)
    }
}
