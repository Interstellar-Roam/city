import Foundation
import os.log

private let logger = Logger(subsystem: "com.citywalk.app", category: "APIService")

// MARK: - API 服务
class APIService {
    static let shared = APIService()
    
    // 基础 URL（开发环境）
    private let baseURL = "http://localhost:8080/api/v1"
    
    private init() {}
    
    // MARK: - 获取路线列表
    func fetchRoutes(tags: [String]? = nil) async throws -> [Route] {
        var urlComponents = URLComponents(string: "\(baseURL)/routes")!
        
        // 添加标签参数
        if let tags = tags, !tags.isEmpty {
            urlComponents.queryItems = [
                URLQueryItem(name: "tags", value: tags.joined(separator: ","))
            ]
        }
        
        let url = urlComponents.url!
        
        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw APIError.invalidResponse
            }
            
            // 打印原始 JSON（调试用）
            if let jsonString = String(data: data, encoding: .utf8) {
                print("📥 收到的 JSON: \(jsonString)")
            }
            
            // 解析分页响应
            let paginatedResponse = try JSONDecoder.routeDecoder.decode(
                PaginatedResponse<Route>.self,
                from: data
            )
            print("✅ 解析成功，共 \(paginatedResponse.items.count) 条路线")
            return paginatedResponse.items
            
        } catch let DecodingError.dataCorrupted(context) {
            print("❌ 数据损坏: \(context.debugDescription)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError
        } catch let DecodingError.keyNotFound(key, context) {
            print("❌ 键不存在: \(key.stringValue)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            print("   描述: \(context.debugDescription)")
            throw APIError.decodingError
        } catch let DecodingError.typeMismatch(type, context) {
            print("❌ 类型不匹配: 期望 \(type)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError
        } catch let DecodingError.valueNotFound(type, context) {
            print("❌ 值不存在: \(type)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError
        } catch {
            print("❌ 其他错误: \(error.localizedDescription)")
            throw APIError.decodingError
        }
    }
    
    // MARK: - 获取路线详情
    func fetchRoute(id: String) async throws -> Route {
        let url = URL(string: "\(baseURL)/routes/\(id)")!
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        let route = try JSONDecoder.routeDecoder.decode(Route.self, from: data)
        return route
    }
    
    // MARK: - 搜索路线
    func searchRoutes(keyword: String) async throws -> [Route] {
        // 使用查询参数方式：/routes/search?keyword=xxx
        var components = URLComponents(string: "\(baseURL)/routes/search")!
        components.queryItems = [URLQueryItem(name: "keyword", value: keyword)]
        
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        
        print("🔍 搜索 URL: \(url.absoluteString)")
        
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        // 打印原始 JSON（调试用）
        if let jsonString = String(data: data, encoding: .utf8) {
            print("📥 搜索结果 JSON (前500字符): \(String(jsonString.prefix(500)))")
        }
        
        // 后端搜索返回 {"success": true, "total": 1, "data": [...]}
        do {
            let searchResponse = try JSONDecoder.routeDecoder.decode(
                SearchResponse<Route>.self,
                from: data
            )
            print("✅ 搜索成功，共 \(searchResponse.data.count) 条路线")
            return searchResponse.data
        } catch let DecodingError.dataCorrupted(context) {
            print("❌ 数据损坏: \(context.debugDescription)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError
        } catch let DecodingError.keyNotFound(key, context) {
            print("❌ 键不存在: \(key.stringValue)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            print("   描述: \(context.debugDescription)")
            throw APIError.decodingError
        } catch let DecodingError.typeMismatch(type, context) {
            print("❌ 类型不匹配: 期望 \(type)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            print("   描述: \(context.debugDescription)")
            throw APIError.decodingError
        } catch let DecodingError.valueNotFound(type, context) {
            print("❌ 值不存在: \(type)")
            print("   路径: \(context.codingPath.map { $0.stringValue }.joined(separator: "."))")
            throw APIError.decodingError
        } catch {
            print("❌ 其他错误: \(error.localizedDescription)")
            throw APIError.decodingError
        }
    }
    
    // MARK: - 获取高德地图配置
    func fetchAmapConfig() async throws -> AmapConfig {
        let url = URL(string: "\(baseURL)/config/amap")!
        
        let (data, _) = try await URLSession.shared.data(from: url)
        
        let config = try JSONDecoder().decode(AmapConfig.self, from: data)
        return config
    }
    
    // MARK: - AI流式搜索（支持会话）
    func streamSearch(
        query: String,
        userId: String = "ios_user",
        sessionId: String? = nil,
        onEvent: @escaping (AIStreamEvent) -> Void
    ) async throws {
        let url = URL(string: "\(baseURL)/search/stream")!

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = [
            "query": query,
            "user_id": userId,
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
            
            // 尝试将累积的数据解码为字符串
            if let decoded = String(data: buffer, encoding: .utf8) {
                lineBuffer = decoded
                
                // 检查是否有完整的行
                while let newlineRange = lineBuffer.range(of: "\n") {
                    let line = String(lineBuffer[..<newlineRange.lowerBound])
                    lineBuffer = String(lineBuffer[newlineRange.upperBound...])
                    
                    // 清空已处理的 buffer
                    if let remainingData = lineBuffer.data(using: .utf8) {
                        buffer = remainingData
                    }
                    
                    let trimmed = line.trimmingCharacters(in: .whitespaces)
                    guard !trimmed.isEmpty, !trimmed.hasPrefix(":") else { continue }
                    
                    if trimmed.hasPrefix("data: ") {
                        let jsonStr = String(trimmed.dropFirst(6))
                        NSLog("📡 SSE 数据: %@", jsonStr)
                        if let data = jsonStr.data(using: .utf8) {
                            do {
                                let event = try JSONDecoder().decode(AIStreamEvent.self, from: data)
                                NSLog("✅ 解码成功: type=%@, content长度=%d", event.type, event.content?.count ?? 0)
                                if let content = event.content {
                                    NSLog("📝 内容预览: %@", String(content.prefix(50)))
                                }
                                onEvent(event)
                            } catch {
                                NSLog("❌ 解码失败: %@, JSON: %@", error.localizedDescription, jsonStr)
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
    let routes: [AIRouteRecommend]?  // 直接从后端接收路线数据
    let sessionId: String?  // 会话 ID

    var eventType: EventType {
        switch type {
        case "text": return .text
        case "tool_call": return .toolCall
        case "tool_result": return .toolResult
        case "done": return .done
        case "error": return .error
        case "user_context": return .userContext
        default: return .unknown
        }
    }

    enum EventType {
        case text
        case toolCall
        case toolResult
        case done
        case error
        case userContext
        case unknown
    }
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

// MARK: - API 错误
enum APIError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case decodingError
    case networkError(String)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "无效的 URL"
        case .invalidResponse:
            return "服务器响应错误"
        case .decodingError:
            return "数据解析错误"
        case .networkError(let message):
            return "网络错误: \(message)"
        }
    }
}

// MARK: - 日期解码策略
extension JSONDecoder {
    static let routeDecoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)
            
            print("📅 尝试解析日期: \(dateString)")
            
            // 尝试多种日期格式
            let formatters: [(DateFormatter, String)] = [
                // 格式1: ISO8601 带毫秒和时区 (2026-04-04T12:21:13.623Z)
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSSZ"), "ISO8601带毫秒时区"),
                // 格式2: ISO8601 带微秒无时区 (2026-04-04T12:21:13.623000)
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSSSSS"), "ISO8601带微秒无时区"),
                // 格式3: ISO8601 带毫秒无时区 (2026-04-04T12:21:13.623)
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSS"), "ISO8601带毫秒无时区"),
                // 格式4: ISO8601 无毫秒带时区 (2026-04-04T12:21:13Z)
                (createFormatter("yyyy-MM-dd'T'HH:mm:ssZ"), "ISO8601无毫秒时区"),
                // 格式5: ISO8601 无毫秒无时区 (2026-04-04T12:21:13)
                (createFormatter("yyyy-MM-dd'T'HH:mm:ss"), "ISO8601无毫秒无时区"),
            ]
            
            for (formatter, name) in formatters {
                if let date = formatter.date(from: dateString) {
                    print("✅ 使用 \(name) 解析成功")
                    return date
                }
            }
            
            // 最后尝试 ISO8601DateFormatter
            let iso8601 = ISO8601DateFormatter()
            iso8601.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = iso8601.date(from: dateString) {
                print("✅ 使用 ISO8601DateFormatter 解析成功")
                return date
            }
            
            iso8601.formatOptions = [.withInternetDateTime]
            if let date = iso8601.date(from: dateString) {
                print("✅ 使用 ISO8601DateFormatter (无毫秒) 解析成功")
                return date
            }
            
            print("❌ 无法解析日期: \(dateString)")
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "无法解析日期: \(dateString)")
        }
        return decoder
    }()
    
    private static func createFormatter(_ format: String) -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = format
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter
    }
}

// MARK: - 会话管理
extension APIService {
    /// 获取用户的会话列表
    func fetchUserSessions(userId: String, limit: Int = 20) async throws -> [ChatSession] {
        var components = URLComponents(string: "\(baseURL)/sessions/user/\(userId)")!
        components.queryItems = [
            URLQueryItem(name: "limit", value: String(limit))
        ]

        guard let url = components.url else {
            throw APIError.invalidURL
        }

        let (data, _) = try await URLSession.shared.data(from: url)

        let response = try JSONDecoder().decode(SessionsResponse.self, from: data)
        return response.sessions
    }

    /// 获取会话详情（包含消息历史）
    func fetchSession(sessionId: String) async throws -> ChatSessionDetail {
        let url = URL(string: "\(baseURL)/sessions/\(sessionId)")!

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        return try JSONDecoder.routeDecoder.decode(ChatSessionDetail.self, from: data)
    }
}

// MARK: - 会话模型
struct ChatSession: Codable, Identifiable {
    let id: String
    let userId: String
    let title: String?
    let createdAt: Date
    let updatedAt: Date
    let messageCount: Int
    let lastMessage: String?

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case userId = "user_id"
        case title
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case messageCount = "message_count"
        case lastMessage = "last_message"
    }
}

struct ChatSessionDetail: Codable {
    let id: String
    let userId: String
    let title: String?
    let messages: [ChatMessageRecord]
    let createdAt: Date
    let updatedAt: Date
    let messageCount: Int

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case userId = "user_id"
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

struct SessionsResponse: Codable {
    let success: Bool
    let total: Int
    let sessions: [ChatSession]
}

/// 用于解码任意 JSON 值
struct AnyCodable: Codable {
    let value: Any

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let string = try? container.decode(String.self) {
            value = string
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            value = ""
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let string = value as? String {
            try container.encode(string)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        }
    }
}
