import Foundation

// MARK: - 用户信息模型
struct UserProfile: Codable {
    let phone: String
    let nickname: String?
    let avatar: String?
    let stats: UserStats

    var displayName: String {
        if let nickname = nickname, !nickname.isEmpty {
            return nickname
        }
        // 手机号脱敏
        let p = phone
        guard p.count >= 11 else { return p }
        let start = p.prefix(3)
        let end = p.suffix(4)
        return "\(start)****\(end)"
    }
}

struct UserStats: Codable {
    let totalDistanceKm: Double
    let routeCount: Int
    let favoriteCount: Int

    enum CodingKeys: String, CodingKey {
        case totalDistanceKm = "total_distance_km"
        case routeCount = "route_count"
        case favoriteCount = "favorite_count"
    }

    var formattedDistance: String {
        if totalDistanceKm >= 100 {
            return String(format: "%.0f km", totalDistanceKm)
        } else if totalDistanceKm >= 1 {
            return String(format: "%.1f km", totalDistanceKm)
        } else {
            return "0 km"
        }
    }
}

// MARK: - 用户更新请求
struct UserUpdateRequest: Codable {
    let nickname: String?
    let avatar: String?
}
