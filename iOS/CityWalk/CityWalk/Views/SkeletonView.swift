import SwiftUI

// MARK: - 骨架屏闪烁动画修饰器
struct ShimmerModifier: ViewModifier {
    @State private var phase: CGFloat = -1

    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { geometry in
                    LinearGradient(
                        gradient: Gradient(stops: [
                            .init(color: .clear, location: 0),
                            .init(color: .white.opacity(0.4), location: 0.5),
                            .init(color: .clear, location: 1)
                        ]),
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                    .mask(content)
                    .offset(x: phase * geometry.size.width)
                }
            )
            .onAppear {
                withAnimation(.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                    phase = 1
                }
            }
    }
}

extension View {
    func shimmer() -> some View {
        modifier(ShimmerModifier())
    }
}

// MARK: - 路线卡片骨架屏（匹配真实 RouteCardView 布局）
struct RouteCardSkeleton: View {
    var body: some View {
        HStack(spacing: 16) {
            // 封面图占位 (100x100)
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemGray5))
                .frame(width: 100, height: 100)
                .shimmer()

            // 文字信息占位
            VStack(alignment: .leading, spacing: 8) {
                // 标题
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 140, height: 16)
                    .shimmer()

                // 描述
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 200, height: 12)
                    .shimmer()

                // 距离/时长
                HStack(spacing: 12) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color(.systemGray5))
                        .frame(width: 60, height: 12)
                        .shimmer()
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color(.systemGray5))
                        .frame(width: 50, height: 12)
                        .shimmer()
                }

                // 标签
                HStack(spacing: 6) {
                    ForEach(0..<3, id: \.self) { _ in
                        RoundedRectangle(cornerRadius: 4)
                            .fill(Color(.systemGray5))
                            .frame(width: 40, height: 18)
                            .shimmer()
                    }
                }
            }

            Spacer()
            Image(systemName: "chevron.right")
                .foregroundColor(Color(.systemGray5))
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.05), radius: 5, x: 0, y: 2)
    }
}
