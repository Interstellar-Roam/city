import Foundation
import CoreLocation

// MARK: - 动态 CodingKey（用于兼容 "_id" / "id" 两种字段名）
private struct DynamicCodingKey: CodingKey {
    var stringValue: String
    var intValue: Int? { nil }
    init?(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { nil }
}

// MARK: - 路线模型
struct Route: Identifiable, Codable, Hashable {
    let id: String
    let name: String
    let description: String?
    let distance: Double  // 米
    let duration: Int?     // 秒
    let difficulty: Difficulty?
    let tags: [String]?
    let coverImage: String?
    let points: [RoutePoint]?
    let pois: [POI]?
    let createdAt: Date?
    let createdBy: String?
    let city: String?
    let district: String?
    let elevationGain: Double?
    let favoritesCount: Int?
    let viewsCount: Int?
    let completionsCount: Int?
    let isPublished: Bool?
    let score: Double?
    let isFeatured: Bool?

    enum CodingKeys: String, CodingKey {
        case id = "_id"
        case name, description, distance, difficulty, tags, city, district, score
        case duration = "estimated_duration"
        case coverImage = "cover"
        case points, pois
        case createdAt = "created_at"
        case createdBy = "created_by"
        case elevationGain = "elevation_gain"
        case favoritesCount = "favorites_count"
        case viewsCount = "views_count"
        case completionsCount = "completions_count"
        case isPublished = "is_published"
        case isFeatured = "is_featured"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        // 兼容 "_id" 和 "id" 两种格式：后端 RouteDetail.model_dump() 输出 "id"，MongoDB 原始数据用 "_id"
        if let underscoreId = try? container.decodeIfPresent(String.self, forKey: .id) {
            // CodingKeys.id = "_id"，从 JSON 的 "_id" 读取
            id = underscoreId
        } else {
            // fallback: 从 JSON 的 "id" 读取（使用动态 key）
            let anyContainer = try decoder.container(keyedBy: DynamicCodingKey.self)
            id = (try? anyContainer.decodeIfPresent(String.self, forKey: DynamicCodingKey(stringValue: "id")!)) ?? ""
        }
        name = try container.decode(String.self, forKey: .name)
        description = try container.decodeIfPresent(String.self, forKey: .description)
        distance = try container.decode(Double.self, forKey: .distance)
        duration = try container.decodeIfPresent(Int.self, forKey: .duration)
        difficulty = try container.decodeIfPresent(Difficulty.self, forKey: .difficulty)
        tags = try container.decodeIfPresent([String].self, forKey: .tags)
        coverImage = try container.decodeIfPresent(String.self, forKey: .coverImage)
        points = try container.decodeIfPresent([RoutePoint].self, forKey: .points)
        pois = try container.decodeIfPresent([POI].self, forKey: .pois)
        createdAt = try container.decodeIfPresent(Date.self, forKey: .createdAt)
        createdBy = try container.decodeIfPresent(String.self, forKey: .createdBy)
        city = try container.decodeIfPresent(String.self, forKey: .city)
        district = try container.decodeIfPresent(String.self, forKey: .district)
        elevationGain = try container.decodeIfPresent(Double.self, forKey: .elevationGain)
        favoritesCount = try container.decodeIfPresent(Int.self, forKey: .favoritesCount)
        viewsCount = try container.decodeIfPresent(Int.self, forKey: .viewsCount)
        completionsCount = try container.decodeIfPresent(Int.self, forKey: .completionsCount)
        isPublished = try container.decodeIfPresent(Bool.self, forKey: .isPublished)
        score = try container.decodeIfPresent(Double.self, forKey: .score)
        isFeatured = try container.decodeIfPresent(Bool.self, forKey: .isFeatured)
    }
    
    // 格式化距离显示
    var formattedDistance: String {
        if distance >= 1000 {
            return String(format: "%.1f km", distance / 1000)
        } else {
            return String(format: "%.0f m", distance)
        }
    }
    
    // 格式化时长显示
    var formattedDuration: String {
        guard let duration = duration else { return "未知" }
        let hours = duration / 3600
        let minutes = (duration % 3600) / 60
        if hours > 0 {
            return "\(hours)小时\(minutes)分钟"
        } else {
            return "\(minutes)分钟"
        }
    }
}

// MARK: - 难度等级
enum Difficulty: String, Codable, Hashable {
    case easy = "easy"
    case medium = "medium"
    case hard = "hard"
    
    // 显示文本
    var displayText: String {
        switch self {
        case .easy: return "简单"
        case .medium: return "中等"
        case .hard: return "困难"
        }
    }
    
    var color: String {
        switch self {
        case .easy: return "green"
        case .medium: return "orange"
        case .hard: return "red"
        }
    }
    
    var icon: String {
        switch self {
        case .easy: return "leaf.fill"
        case .medium: return "flame.fill"
        case .hard: return "mountain.2.fill"
        }
    }
}

// MARK: - 轨迹点
struct RoutePoint: Codable, Hashable {
    let location: Location
    let elevation: Double?
    let timestamp: Date?
    let isWaypoint: Bool?
    let photos: [String]?
    let isEdited: Bool?
    let name: String?
    let description: String?
    
    enum CodingKeys: String, CodingKey {
        case location, elevation, timestamp, photos, name, description
        case isWaypoint = "is_waypoint"
        case isEdited = "is_edited"
    }
}

// MARK: - 位置
struct Location: Codable, Hashable {
    let type: String
    let coordinates: [Double]  // [经度, 纬度]
    
    var longitude: Double { coordinates.count > 0 ? coordinates[0] : 0 }
    var latitude: Double { coordinates.count > 1 ? coordinates[1] : 0 }
    
    var coordinate: CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
}

// MARK: - POI
struct POI: Identifiable, Codable, Hashable {
    let id: String
    let name: String
    let location: Location
    let category: String?
    let poiDescription: String?
    let images: [String]?
    let rating: Double?
    let tags: [String]?
    let amapPoiId: String?
    let distance: Double?
    let type: String?
    let address: String?
    
    enum CodingKeys: String, CodingKey {
        case id, name, location, category, images, rating, tags, distance, type, address
        case poiDescription = "description"
        case amapPoiId = "amap_poi_id"
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        location = try container.decode(Location.self, forKey: .location)
        category = try container.decodeIfPresent(String.self, forKey: .category)
        // description 可能是 String 或其他类型
        if let descString = try? container.decode(String.self, forKey: .poiDescription) {
            poiDescription = descString
        } else {
            poiDescription = nil
        }
        images = try container.decodeIfPresent([String].self, forKey: .images)
        rating = try container.decodeIfPresent(Double.self, forKey: .rating)
        tags = try container.decodeIfPresent([String].self, forKey: .tags)
        amapPoiId = try container.decodeIfPresent(String.self, forKey: .amapPoiId)
        distance = try container.decodeIfPresent(Double.self, forKey: .distance)
        type = try container.decodeIfPresent(String.self, forKey: .type)
        address = try container.decodeIfPresent(String.self, forKey: .address)
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(location, forKey: .location)
        try container.encodeIfPresent(category, forKey: .category)
        try container.encodeIfPresent(poiDescription, forKey: .poiDescription)
        try container.encodeIfPresent(images, forKey: .images)
        try container.encodeIfPresent(rating, forKey: .rating)
        try container.encodeIfPresent(tags, forKey: .tags)
        try container.encodeIfPresent(amapPoiId, forKey: .amapPoiId)
        try container.encodeIfPresent(distance, forKey: .distance)
        try container.encodeIfPresent(type, forKey: .type)
        try container.encodeIfPresent(address, forKey: .address)
    }
}

// MARK: - 路线卡片（用于列表展示）
struct RouteCard: Identifiable {
    let id: String
    let route: Route
    let cityName: String
    let likes: Int
    let views: Int
    let isFeatured: Bool
}
