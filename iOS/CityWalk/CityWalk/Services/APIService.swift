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
    func fetchRoutes() async throws -> [Route] {
        let url = URL(string: "\(baseURL)/routes")!
        
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
    
    // MARK: - AI流式搜索
    func streamSearch(query: String, userId: String = "ios_user", onEvent: @escaping (AIStreamEvent) -> Void) async throws {
        let url = URL(string: "\(baseURL)/search/stream")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "query": query,
            "user_id": userId,
            "session_id": UUID().uuidString
        ]
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
    
    var eventType: EventType {
        switch type {
        case "text": return .text
        case "tool_call": return .toolCall
        case "tool_result": return .toolResult
        case "done": return .done
        case "error": return .error
        default: return .unknown
        }
    }
    
    enum EventType {
        case text
        case toolCall
        case toolResult
        case done
        case error
        case unknown
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
            
            // 尝试 ISO8601 带毫秒
            let iso8601WithMs = ISO8601DateFormatter()
            iso8601WithMs.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = iso8601WithMs.date(from: dateString) {
                print("✅ 使用 ISO8601 带毫秒解析成功")
                return date
            }
            
            // 尝试 ISO8601 不带毫秒
            let iso8601 = ISO8601DateFormatter()
            iso8601.formatOptions = [.withInternetDateTime]
            if let date = iso8601.date(from: dateString) {
                print("✅ 使用 ISO8601 不带毫秒解析成功")
                return date
            }
            
            // 尝试自定义格式 "2026-03-21T14:22:25.108000"
            let custom = DateFormatter()
            custom.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
            custom.locale = Locale(identifier: "en_US_POSIX")
            custom.timeZone = TimeZone(secondsFromGMT: 0)
            if let date = custom.date(from: dateString) {
                print("✅ 使用自定义格式解析成功")
                return date
            }
            
            // 尝试带时区的格式
            let customWithTz = DateFormatter()
            customWithTz.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSSZZZZZ"
            customWithTz.locale = Locale(identifier: "en_US_POSIX")
            if let date = customWithTz.date(from: dateString) {
                print("✅ 使用带时区格式解析成功")
                return date
            }
            
            print("❌ 无法解析日期: \(dateString)")
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "无法解析日期: \(dateString)")
        }
        return decoder
    }()
}
