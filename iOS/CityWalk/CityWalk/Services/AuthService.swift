import Foundation

/// 认证网络服务
class AuthService {
    static let shared = AuthService()

    private var baseURL: String { AppConfig.apiBaseURL }
    private let decoder = JSONDecoder()

    private init() {}

    // MARK: - 发送验证码

    func sendCode(phone: String) async throws -> APIEmptyResponse {
        let url = URL(string: "\(baseURL)/auth/send-code")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(SendCodeRequest(phone: phone))

        let (data, _) = try await URLSession.shared.data(for: request)
        return try decoder.decode(APIEmptyResponse.self, from: data)
    }

    // MARK: - 登录

    func login(phone: String, code: String) async throws -> TokenPair {
        let url = URL(string: "\(baseURL)/auth/login")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(LoginRequest(phone: phone, code: code))

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decoder.decode(APIResponse<TokenPair>.self, from: data)

        guard response.code == 0, let tokenPair = response.data else {
            throw AuthError.serverError(response.code, response.message)
        }

        // 持久化 Token
        TokenStorage.shared.saveTokens(
            access: tokenPair.accessToken,
            refresh: tokenPair.refreshToken,
            expiresIn: tokenPair.expiresIn,
            phone: phone
        )

        return tokenPair
    }

    // MARK: - 刷新 Token

    func refreshToken() async throws -> TokenPair {
        guard let refresh = TokenStorage.shared.getRefreshToken() else {
            throw AuthError.notLoggedIn
        }

        let url = URL(string: "\(baseURL)/auth/refresh")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(RefreshRequest(refreshToken: refresh))

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decoder.decode(APIResponse<TokenPair>.self, from: data)

        guard response.code == 0, let tokenPair = response.data else {
            // 刷新失败，清除 Token
            if response.code == 2004 {
                TokenStorage.shared.clearAll()
            }
            throw AuthError.serverError(response.code, response.message)
        }

        // 更新 Token
        TokenStorage.shared.saveTokens(
            access: tokenPair.accessToken,
            refresh: tokenPair.refreshToken,
            expiresIn: tokenPair.expiresIn,
            phone: TokenStorage.shared.getPhone() ?? ""
        )

        return tokenPair
    }

    // MARK: - 登出

    func logout() async throws {
        let url = URL(string: "\(baseURL)/auth/logout")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // 带上当前 Token
        if let token = TokenStorage.shared.getAccessToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let _ = try await URLSession.shared.data(for: request)
        TokenStorage.shared.clearAll()
    }
}

// MARK: - 错误

enum AuthError: Error, LocalizedError {
    case notLoggedIn
    case serverError(Int, String)
    case networkError(String)

    var errorDescription: String? {
        switch self {
        case .notLoggedIn:
            return "未登录"
        case .serverError(_, let msg):
            return msg
        case .networkError(let msg):
            return msg
        }
    }
}
