import SwiftUI
import Photos

// MARK: - 路线分享卡片
struct ShareCardView: View {
    let route: Route
    @State private var isSaving = false
    @State private var showToast = false
    @Environment(\.dismiss) private var dismiss

    private let cardWidth: CGFloat = 300

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                // 预览卡片
                cardView
                    .frame(width: cardWidth, height: cardWidth * 1.25)
                    .cornerRadius(20)
                    .shadow(color: .black.opacity(0.15), radius: 10, y: 4)

                // 保存按钮
                Button(action: saveToPhotos) {
                    HStack(spacing: 8) {
                        if isSaving {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Image(systemName: "square.and.arrow.down.fill")
                        }
                        Text(isSaving ? "保存中..." : "保存到相册")
                    }
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 32)
                    .padding(.vertical, 14)
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color.orange)
                    )
                }
                .disabled(isSaving)
            }
            .navigationTitle("分享路线")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") { dismiss() }
                }
            }
            .overlay(
                Group {
                    if showToast {
                        toastView
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                    }
                },
                alignment: .bottom
            )
            .animation(.easeInOut, value: showToast)
        }
    }

    // MARK: - 卡片视图
    private var cardView: some View {
        ZStack(alignment: .bottomLeading) {
            // 背景
            if let cover = route.coverImage, !cover.isEmpty {
                // 有封面图时显示纯色占位（Base64 图片渲染复杂，用渐变色替代也可）
                gradientBackground
            } else {
                gradientBackground
            }

            // 底部渐变遮罩
            LinearGradient(
                colors: [.clear, .black.opacity(0.7)],
                startPoint: .center,
                endPoint: .bottom
            )

            // 信息
            VStack(alignment: .leading, spacing: 8) {
                Text(route.name)
                    .font(.system(size: 22, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                HStack(spacing: 12) {
                    Label(route.formattedDistance, systemImage: "point.topleft.down.to.point.bottomright.curvepath")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.9))

                    if let duration = route.duration {
                        Label(route.formattedDuration, systemImage: "clock")
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.9))
                    }

                    if let diff = route.difficulty {
                        Label(diff.displayText, systemImage: diff.icon)
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.9))
                    }
                }

                // App 水印
                HStack {
                    Image(systemName: "figure.walk.circle.fill")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.6))
                    Text("CityWalk · 发现城市的每一处风景")
                        .font(.caption2)
                        .foregroundColor(.white.opacity(0.5))
                    Spacer()
                }
            }
            .padding(20)
        }
        .frame(width: cardWidth, height: cardWidth * 1.25)
    }

    // MARK: - 渐变背景
    private var gradientBackground: some View {
        LinearGradient(
            colors: [
                Color(hue: abs(Double(route.name.hashValue % 360)) / 360.0, saturation: 0.6, brightness: 0.7),
                Color(hue: abs(Double((route.name + "end").hashValue % 360)) / 360.0, saturation: 0.7, brightness: 0.5)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }

    // MARK: - Toast
    private var toastView: some View {
        HStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundColor(.green)
            Text("已保存到相册")
                .font(.subheadline)
                .foregroundColor(.white)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
        .background(Capsule().fill(Color.black.opacity(0.8)))
        .padding(.bottom, 40)
    }

    // MARK: - 保存
    private func saveToPhotos() {
        isSaving = true
        let renderer = ImageRenderer(content: cardView)
        renderer.scale = UIScreen.main.scale

        if let image = renderer.uiImage {
            PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            } completionHandler: { success, error in
                DispatchQueue.main.async {
                    isSaving = false
                    if success {
                        showToast = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            showToast = false
                            dismiss()
                        }
                    }
                }
            }
        } else {
            isSaving = false
        }
    }
}
