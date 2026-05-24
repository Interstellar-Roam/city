import Foundation

// MARK: - 认证请求模型

struct SendCodeRequest: Codable {
    let phone: String
}

struct LoginRequest: Codable {
    let phone: String
    let code: String
}

struct RefreshRequest: Codable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

// MARK: - 认证响应模型

struct TokenPair: Codable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresIn: Int
    let user: AuthUser

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
        case user
    }
}

struct AuthUser: Codable {
    let id: String
    let phone: String
}

// MARK: - 统一 API 响应包装

struct APIResponse<T: Codable>: Codable {
    let code: Int
    let message: String
    let data: T?
}

/// 空数据响应（仅 code + message）
struct APIEmptyResponse: Codable {
    let code: Int
    let message: String
}
