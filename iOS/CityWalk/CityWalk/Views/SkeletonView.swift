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

// MARK: - 路线卡片骨架屏
struct RouteCardSkeleton: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // 封面图占位
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemGray5))
                .frame(width: 100, height: 100)
                .shimmer()

            VStack(alignment: .leading, spacing: 6) {
                // 标题
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 80, height: 14)
                    .shimmer()

                // 距离/时长
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 120, height: 12)
                    .shimmer()

                // 标签
                RoundedRectangle(cornerRadius: 4)
                    .fill(Color(.systemGray5))
                    .frame(width: 60, height: 10)
                    .shimmer()
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 8)
        }
        .frame(width: 140)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(.systemGray6))
        )
        .clipped()
    }
}
