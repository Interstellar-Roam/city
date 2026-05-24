import Foundation
import os.log

private let logger = Logger(subsystem: "com.citywalk.app", category: "APIService")

// MARK: - API 服务
class APIService {
    static let shared = APIService()

    /// 基础 URL
    private var baseURL: String { AppConfig.apiBaseURL }

    /// 当前认证 Token
    private var authToken: String? { TokenStorage.shared.getAccessToken() }

    private init() {}

    // MARK: - 认证请求构建

    func authenticatedRequest(for url: URL, method: String = "GET", body: Data? = nil) throws -> URLRequest {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body = body {
            request.httpBody = body
        }
        return request
    }

    // MARK: - 响应解析

    /// 解析新格式：{"code": 0, "message": "ok", "data": {...}}
    func decodeResponse<T: Codable>(_ type: T.Type, from data: Data) throws -> APIResponse<T> {
        let decoder = JSONDecoder.routeDecoder
        return try decoder.decode(APIResponse<T>.self, from: data)
    }

    // MARK: - 获取路线列表
    func fetchRoutes(tags: [String]? = nil) async throws -> [Route] {
        var urlComponents = URLComponents(string: "\(baseURL)/routes")!

        if let tags = tags, !tags.isEmpty {
            urlComponents.queryItems = [
                URLQueryItem(name: "tags", value: tags.joined(separator: ","))
            ]
        }

        guard let url = urlComponents.url else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decodeResponse(PaginatedData.self, from: data)

        guard response.code == 0, let paginated = response.data else {
            throw APIError.networkError(response.message)
        }
        return paginated.items
    }

    // MARK: - 获取我的路线列表
    func fetchMyRoutes(page: Int = 1, pageSize: Int = 20) async throws -> PaginatedData {
        var urlComponents = URLComponents(string: "\(baseURL)/routes/mine")!
        urlComponents.queryItems = [
            URLQueryItem(name: "page", value: String(page)),
            URLQueryItem(name: "page_size", value: String(pageSize))
        ]

        guard let url = urlComponents.url else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decodeResponse(PaginatedData.self, from: data)

        guard response.code == 0, let paginated = response.data else {
            throw APIError.networkError(response.message)
        }
        return paginated
    }

    // MARK: - 获取路线详情
    func fetchRoute(id: String) async throws -> Route {
        guard let url = URL(string: "\(baseURL)/routes/\(id)") else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decodeResponse(Route.self, from: data)

        guard response.code == 0, let route = response.data else {
            throw APIError.networkError(response.message)
        }
        return route
    }

    // MARK: - 搜索路线
    func searchRoutes(keyword: String) async throws -> [Route] {
        var components = URLComponents(string: "\(baseURL)/routes/search")!
        components.queryItems = [URLQueryItem(name: "keyword", value: keyword)]

        guard let url = components.url else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)

        let (data, _) = try await URLSession.shared.data(for: request)

        // 搜索返回: {"code": 0, "message": "ok", "data": {"total": N, "items": [...]}}
        let response = try decodeResponse(SearchResult.self, from: data)

        guard response.code == 0, let result = response.data else {
            throw APIError.networkError(response.message)
        }
        return result.items
    }

    // MARK: - 获取高德地图配置
    func fetchAmapConfig() async throws -> AmapConfig {
        guard let url = URL(string: "\(baseURL)/config/amap") else { throw APIError.invalidURL }
        let (data, _) = try await URLSession.shared.data(from: url)

        let config = try JSONDecoder().decode(AmapConfig.self, from: data)
        return config
    }

    // MARK: - AI流式搜索
    func streamSearch(
        query: String,
        sessionId: String? = nil,
        onEvent: @escaping (AIStreamEvent) -> Void
    ) async throws {
        guard let url = URL(string: "\(baseURL)/search/stream") else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body: [String: Any] = [
            "query": query,
            "include_history": true
        ]
        if let sessionId = sessionId {
            body["session_id"] = sessionId
        }
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        let (bytes, response) = try await URLSession.shared.bytes(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        var buffer = Data()
        var lineBuffer = ""

        for try await byte in bytes {
            buffer.append(byte)

            if let decoded = String(data: buffer, encoding: .utf8) {
                lineBuffer = decoded

                while let newlineRange = lineBuffer.range(of: "\n") {
                    let line = String(lineBuffer[..<newlineRange.lowerBound])
                    lineBuffer = String(lineBuffer[newlineRange.upperBound...])

                    if let remainingData = lineBuffer.data(using: .utf8) {
                        buffer = remainingData
                    }

                    let trimmed = line.trimmingCharacters(in: .whitespaces)
                    guard !trimmed.isEmpty, !trimmed.hasPrefix(":") else { continue }

                    if trimmed.hasPrefix("data: ") {
                        let jsonStr = String(trimmed.dropFirst(6))
                        if let data = jsonStr.data(using: .utf8) {
                            do {
                                let event = try JSONDecoder().decode(AIStreamEvent.self, from: data)
                                onEvent(event)
                            } catch {
                                print("SSE decode error: \(error)")
                            }
                        }
                    }
                }
            }
        }
    }
}

// MARK: - AI流式事件
struct AIStreamEvent: Codable {
    let type: String
    let content: String?
    let name: String?
    let arguments: String?
    let result: String?
    let message: String?
    let routes: [AIRouteRecommend]?
    let sessionId: String?

    var eventType: EventType {
        switch type {
        case "text": return .text
        case "tool_call": return .toolCall
        case "tool_result": return .toolResult
        case "route_recommendations": return .routeRecommendations
        case "done": return .done
        case "error": return .error
        default: return .unknown
        }
    }

    enum EventType: CaseIterable {
        case text, toolCall, toolResult, routeRecommendations, done, error, unknown
    }
}

// MARK: - 内部响应模型

/// 分页数据
struct PaginatedData: Codable {
    let items: [Route]
    let total: Int
    let page: Int
    let pageSize: Int
    let hasMore: Bool

    enum CodingKeys: String, CodingKey {
        case items, total, page
        case pageSize = "page_size"
        case hasMore = "has_more"
    }
}

/// 搜索结果
struct SearchResult: Codable {
    let total: Int
    let items: [Route]
}

// MARK: - AI推荐路线
struct AIRouteRecommend: Codable, Identifiable {
    let id: String
    let name: String
    let description: String?
    let distance: Double?
    let elevationGain: Double?
    let estimatedDuration: Int?
    let difficulty: String?
    let city: String?
    let favoritesCount: Int?
    let previewImage: String?
    let tags: [String]?

    enum CodingKeys: String, CodingKey {
        case id, name, description, distance, difficulty, city, tags
        case elevationGain = "elevation_gain"
        case estimatedDuration = "estimated_duration"
        case favoritesCount = "favorites_count"
        case previewImage = "preview_image"
    }
}

// MARK: - 高德地图配置
struct AmapConfig: Codable {
    let apiKey: String
    let securityKey: String

    enum CodingKeys: String, CodingKey {
        case apiKey = "api_key"
        case securityKey = "security_key"
    }
}

// MARK: - 会话管理
extension APIService {
    func fetchUserSessions(limit: Int = 20) async throws -> [ChatSession] {
        var components = URLComponents(string: "\(baseURL)/sessions")!
        components.queryItems = [
            URLQueryItem(name: "limit", value: String(limit))
        ]

        guard let url = components.url else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decodeResponse(SessionsData.self, from: data)

        guard response.code == 0, let sessionsData = response.data else {
            throw APIError.networkError(response.message)
        }
        return sessionsData.sessions
    }

    func fetchSession(sessionId: String) async throws -> ChatSessionDetail {
        guard let url = URL(string: "\(baseURL)/sessions/\(sessionId)") else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)

        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decodeResponse(ChatSessionDetail.self, from: data)

        guard response.code == 0, let detail = response.data else {
            throw APIError.networkError(response.message)
        }
        return detail
    }
}

/// 会话数据
struct SessionsData: Codable {
    let sessions: [ChatSession]
}

// MARK: - 会话模型
struct ChatSession: Codable, Identifiable {
    let id: String
    let title: String?
    let createdAt: Date
    let updatedAt: Date
    let messageCount: Int
    let lastMessage: String?

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case title
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case messageCount = "message_count"
        case lastMessage = "last_message"
    }
}

struct ChatSessionDetail: Codable {
    let id: String
    let title: String?
    let messages: [ChatMessageRecord]
    let createdAt: Date
    let updatedAt: Date
    let messageCount: Int

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case title, messages
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case messageCount = "message_count"
    }
}

struct ChatMessageRecord: Codable {
    let role: String
    let content: String
    let timestamp: Date
    let metadata: [String: AnyCodable]?

    enum CodingKeys: String, CodingKey {
        case role, content, timestamp, metadata
    }
}

struct AnyCodable: Codable {
    let value: Any

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let s = try? container.decode(String.self) { value = s }
        else if let i = try? container.decode(Int.self) { value = i }
        else if let d = try? container.decode(Double.self) { value = d }
        else if let b = try? container.decode(Bool.self) { value = b }
        else { value = "" }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        if let s = value as? String { try c.encode(s) }
        else if let i = value as? Int { try c.encode(i) }
        else if let d = value as? Double { try c.encode(d) }
        else if let b = value as? Bool { try c.encode(b) }
    }
}

// MARK: - Phase 1 新增 API

/// 精选路线响应
struct FeaturedData: Codable {
    let items: [Route]
    let total: Int
}

extension APIService {
    /// 获取精选路线
    func fetchFeaturedRoutes() async throws -> [Route] {
        guard let url = URL(string: "\(baseURL)/routes/featured") else { throw APIError.invalidURL }
        let request = try authenticatedRequest(for: url)
        let (data, _) = try await URLSession.shared.data(for: request)
        let response = try decodeResponse(FeaturedData.self, from: data)
        guard response.code == 0, let featured = response.data else {
            throw APIError.networkError(response.message)
        }
        return featured.items
    }

    /// 更新路线信息
    func updateRoute(id: String, name: String?, description: String?, difficulty: String?, tags: [String]?, city: String?) async throws {
        guard let url = URL(string: "\(baseURL)/routes/\(id)") else { throw APIError.invalidURL }

        var body: [String: Any] = [:]
        if let name = name { body["name"] = name }
        if let description = description { body["description"] = description }
        if let difficulty = difficulty { body["difficulty"] = difficulty }
        if let tags = tags { body["tags"] = tags }
        if let city = city { body["city"] = city }

        let bodyData = try? JSONSerialization.data(withJSONObject: body)
        var request = try authenticatedRequest(for: url, method: "PUT", body: bodyData)
        let (_, _) = try await URLSession.shared.data(for: request)
    }

    /// 上传封面图
    func uploadCoverImage(routeId: String, imageBase64: String) async throws {
        guard let url = URL(string: "\(baseURL)/routes/\(routeId)/cover") else { throw APIError.invalidURL }
        let body = ["image": imageBase64]
        let bodyData = try? JSONSerialization.data(withJSONObject: body)
        var request = try authenticatedRequest(for: url, method: "POST", body: bodyData)
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
    }
}

// MARK: - API 错误
enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case decodingError
    case networkError(String)

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "无效的 URL"
        case .invalidResponse: return "服务器响应错误"
        case .decodingError: return "数据解析错误"
        case .networkError(let m): return m
        }
    }
}

// MARK: - 日期解码
extension JSONDecoder {
    static let routeDecoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)

            let formatters: [(DateFormatter, String)] = [
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSSZ"), "ISO带毫秒时区"),
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSSSSS"), "ISO带微秒"),
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSS"), "ISO带毫秒"),
                (createFormatter("yyyy-MM-dd'T'HH:mm:ssZ"), "ISO无毫秒时区"),
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss"), "ISO无毫秒"),
            ]

            for (f, _) in formatters {
                if let date = f.date(from: dateString) { return date }
            }

            let iso8601 = ISO8601DateFormatter()
            iso8601.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = iso8601.date(from: dateString) { return date }

            iso8601.formatOptions = [.withInternetDateTime]
            if let date = iso8601.date(from: dateString) { return date }

            throw DecodingError.dataCorruptedError(in: container, debugDescription: "无法解析日期: \(dateString)")
        }
        return decoder
    }()

    private static func createFormatter(_ format: String) -> DateFormatter {
        let f = DateFormatter()
        f.dateFormat = format
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }
}
