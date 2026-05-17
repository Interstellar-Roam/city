import SwiftUI

// MARK: - ROAM 风格设计令牌
enum AppTheme {
    // 品牌色
    static let primary = Color(red: 0.18, green: 0.35, blue: 0.24)       // #2D5A3D 深绿
    static let accent = Color(red: 0.24, green: 0.60, blue: 0.44)       // #3D9970 翠绿
    static let secondary = Color(red: 1.0, green: 0.55, blue: 0.26)     // #FF8C42 活力橙
    
    // 背景色
    static let background = Color.black                                    // #000000 纯黑
    static let surface = Color(red: 0.11, green: 0.11, blue: 0.12)      // #1C1C1E 卡片/表面
    static let elevated = Color(red: 0.17, green: 0.17, blue: 0.18)     // #2C2C2E 抬起层
    
    // 文字色
    static let textPrimary = Color.white
    static let textSecondary = Color(red: 0.56, green: 0.56, blue: 0.57) // #8E8E93
    static let textTertiary = Color(red: 0.39, green: 0.39, blue: 0.40)  // #636366
    
    // 功能色
    static let success = Color(red: 0.19, green: 0.82, blue: 0.35)       // #30D158
    static let warning = Color(red: 1.0, green: 0.62, blue: 0.04)        // #FF9F0A
    static let error = Color(red: 1.0, green: 0.27, blue: 0.23)          // #FF453A
    static let info = Color(red: 0.04, green: 0.52, blue: 1.0)           // #0A84FF
    
    // 边框/分割线
    static let divider = Color(red: 0.22, green: 0.22, blue: 0.23)       // #38383A
    static let border = Color(red: 0.28, green: 0.28, blue: 0.29)        // #48484A
    
    // 地图路线色
    static let routeCompleted = Color(red: 0.19, green: 0.82, blue: 0.35) // #30D158 绿色
    static let routePlanning = Color(red: 1.0, green: 0.55, blue: 0.26)  // #FF8C42 橙色
    static let routeRemaining = Color(red: 0.04, green: 0.52, blue: 1.0) // #0A84FF 蓝色
    
    // AI 标识色
    static let aiGradient1 = Color(red: 0.18, green: 0.35, blue: 0.24)   // 深绿
    static let aiGradient2 = Color(red: 0.24, green: 0.60, blue: 0.44)   // 翠绿
    
    // 用户消息气泡
    static let userBubble = Color(red: 0.18, green: 0.35, blue: 0.24)    // #2D5A3D
    
    // 圆角
    static let cornerRadiusSmall: CGFloat = 8
    static let cornerRadiusMedium: CGFloat = 16
    static let cornerRadiusLarge: CGFloat = 24
    
    // 难度颜色
    static func difficultyColor(_ difficulty: Difficulty) -> Color {
        switch difficulty {
        case .easy: return success
        case .medium: return warning
        case .hard: return error
        }
    }
}
