import Foundation
import os.log

private let authLogger = Logger(subsystem: "com.citywalk.app", category: "AuthService")

/// 认证网络服务
class AuthService {
    static let shared = AuthService()

    private var baseURL: String { AppConfig.apiBaseURL }
    private let decoder = JSONDecoder()

    private init() {}

    // MARK: - 响应调试

    private func logResponse(_ data: Data, response: URLResponse?, function: String = #function) {
        let httpStatus = (response as? HTTPURLResponse)?.statusCode ?? -1
        let body = String(data: data, encoding: .utf8) ?? "(non-utf8)"
        authLogger.error("[\(function)] HTTP \(httpStatus) | body: \(body)")
    }

    // MARK: - 发送验证码

    func sendCode(phone: String) async throws -> APIEmptyResponse {
        let urlStr = "\(baseURL)/auth/send-code"
        let url = URL(string: urlStr)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(SendCodeRequest(phone: phone))

        let (data, urlResponse) = try await URLSession.shared.data(for: request)
        logResponse(data, response: urlResponse)
        let httpStatus = (urlResponse as? HTTPURLResponse)?.statusCode ?? -1
        let rawBody = String(data: data, encoding: .utf8) ?? "(empty)"

        guard httpStatus == 200 else {
            throw AuthError.networkError("请求失败[\(urlStr) HTTP\(httpStatus)]: \(rawBody.prefix(100))")
        }

        do {
            return try decoder.decode(APIEmptyResponse.self, from: data)
        } catch {
            authLogger.error("[sendCode] decode failed: \(error)")
            throw AuthError.networkError("验证码解析失败: \(rawBody.prefix(200))")
        }
    }

    // MARK: - 登录

    func login(phone: String, code: String) async throws -> TokenPair {
        let urlStr = "\(baseURL)/auth/login"
        let url = URL(string: urlStr)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(LoginRequest(phone: phone, code: code))

        let (data, urlResponse) = try await URLSession.shared.data(for: request)
        logResponse(data, response: urlResponse)
        let httpStatus = (urlResponse as? HTTPURLResponse)?.statusCode ?? -1
        let rawBody = String(data: data, encoding: .utf8) ?? "(empty)"

        guard httpStatus == 200 else {
            throw AuthError.networkError("请求失败[\(urlStr) HTTP\(httpStatus)]: \(rawBody.prefix(100))")
        }

        let response: APIResponse<TokenPair>
        do {
            response = try decoder.decode(APIResponse<TokenPair>.self, from: data)
        } catch {
            authLogger.error("[login] decode failed: \(error)")
            throw AuthError.networkError("登录解析失败: \(rawBody.prefix(200))")
        }

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
        TokenStorage.shared.saveUserId(tokenPair.user.id)

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

        let (data, urlResponse) = try await URLSession.shared.data(for: request)
        logResponse(data, response: urlResponse)
        let httpStatus = (urlResponse as? HTTPURLResponse)?.statusCode ?? -1
        let rawBody = String(data: data, encoding: .utf8) ?? "(empty)"

        let response: APIResponse<TokenPair>
        do {
            response = try decoder.decode(APIResponse<TokenPair>.self, from: data)
        } catch {
            throw AuthError.networkError("刷新Token解析失败[HTTP\(httpStatus)]: \(rawBody.prefix(200))")
        }

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
