import SwiftUI
import PhotosUI

// MARK: - 路线编辑页
struct EditRouteView: View {
    let route: Route
    @Environment(\.dismiss) private var dismiss

    @State private var name: String
    @State private var description: String
    @State private var difficulty: String
    @State private var tags: [String]
    @State private var city: String
    @State private var coverURL: String

    @State private var selectedPhoto: PhotosPickerItem?
    @State private var selectedImageData: Data?
    @State private var isSaving = false
    @State private var errorMessage: String?
    @State private var isPublished: Bool

    private let difficultyOptions = ["easy", "medium", "hard"]
    private let difficultyLabels = ["简单", "中等", "困难"]
    private let tagOptions = ["徒步", "跑步", "骑行", "公园", "海边", "越野跑", "城市", "山地"]

    init(route: Route) {
        self.route = route
        _name = State(initialValue: route.name)
        _description = State(initialValue: route.description ?? "")
        _difficulty = State(initialValue: route.difficulty?.rawValue ?? "medium")
        _tags = State(initialValue: route.tags ?? [])
        _city = State(initialValue: route.city ?? "")
        _coverURL = State(initialValue: route.coverImage ?? "")
        _isPublished = State(initialValue: route.isPublished ?? true)
    }

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    coverSection.padding(.top, 8)

                    // 名称
                    VStack(alignment: .leading, spacing: 6) {
                        Text("路线名称").font(.caption).foregroundColor(.secondary)
                        TextField("路线名称", text: $name).textFieldStyle(.roundedBorder)
                    }
                    // 描述
                    VStack(alignment: .leading, spacing: 6) {
                        Text("描述").font(.caption).foregroundColor(.secondary)
                        TextEditor(text: $description)
                            .frame(minHeight: 80)
                            .padding(4)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.secondary.opacity(0.2)))
                    }
                    // 难度
                    VStack(alignment: .leading, spacing: 6) {
                        Text("难度").font(.caption).foregroundColor(.secondary)
                        HStack(spacing: 8) {
                            ForEach(0..<3, id: \.self) { i in
                                Button(action: { difficulty = difficultyOptions[i] }) {
                                    HStack(spacing: 4) {
                                        Image(systemName: difficulty == difficultyOptions[i] ? "circle.fill" : "circle").font(.caption)
                                        Text(difficultyLabels[i]).font(.subheadline)
                                    }
                                    .padding(.horizontal, 16).padding(.vertical, 10)
                                    .background(RoundedRectangle(cornerRadius: 10)
                                        .fill(difficulty == difficultyOptions[i] ? Color.orange.opacity(0.15) : Color(.systemGray6)))
                                    .foregroundColor(difficulty == difficultyOptions[i] ? .orange : .secondary)
                                }
                            }
                        }
                    }
                    // 标签
                    VStack(alignment: .leading, spacing: 6) {
                        Text("标签").font(.caption).foregroundColor(.secondary)
                        LazyVGrid(columns: [GridItem(.adaptive(minimum: 70))], spacing: 8) {
                            ForEach(tagOptions, id: \.self) { tag in
                                let selected = tags.contains(tag)
                                Button(action: {
                                    if selected { tags.removeAll { $0 == tag } } else { tags.append(tag) }
                                }) {
                                    Text(tag).font(.subheadline)
                                        .padding(.horizontal, 12).padding(.vertical, 6)
                                        .background(RoundedRectangle(cornerRadius: 8)
                                            .fill(selected ? Color.orange.opacity(0.15) : Color(.systemGray6)))
                                        .foregroundColor(selected ? .orange : .secondary)
                                }
                            }
                        }
                    }
                    // 城市
                    VStack(alignment: .leading, spacing: 6) {
                        Text("城市").font(.caption).foregroundColor(.secondary)
                        TextField("城市", text: $city).textFieldStyle(.roundedBorder)
                    }

                    // 公开设置
                    VStack(alignment: .leading, spacing: 4) {
                        Toggle(isOn: $isPublished) {
                            Label(isPublished ? "公开路线" : "私密路线", systemImage: isPublished ? "globe.asia.australia" : "lock.fill")
                        }
                        .tint(.orange)
                        Text(isPublished ? "所有人可在发现页看到这条路线" : "仅自己可见，不会出现在发现和搜索中")
                            .font(.caption).foregroundColor(.secondary)
                    }
                    .padding(.vertical, 4)

                    if let error = errorMessage {
                        Text(error).font(.caption).foregroundColor(.red)
                    }
                }
                .padding(.horizontal).padding(.bottom, 40)
            }
            .navigationTitle("编辑路线")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(action: save) {
                        if isSaving { ProgressView() } else { Text("保存") }
                    }
                    .disabled(name.isEmpty || isSaving)
                }
            }
        }
        .onChange(of: selectedPhoto) { newItem in
            Task {
                if let data = try? await newItem?.loadTransferable(type: Data.self) {
                    if let img = UIImage(data: data),
                       let compressed = img.jpegData(compressionQuality: 0.6) {
                        selectedImageData = compressed
                    } else {
                        selectedImageData = data
                    }
                }
            }
        }
    }

    // MARK: - 封面区域
    private var coverSection: some View {
        PhotosPicker(selection: $selectedPhoto, matching: .images) {
            ZStack {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color(.systemGray5))
                    .frame(height: 180)

                // 预览已选择的图片
                if let imgData = selectedImageData, let uiImage = UIImage(data: imgData) {
                    Image(uiImage: uiImage)
                        .resizable()
                        .scaledToFill()
                        .frame(height: 180)
                        .cornerRadius(16)
                        .clipped()
                }

                // 覆盖层
                VStack(spacing: 8) {
                    Image(systemName: selectedImageData != nil ? "arrow.triangle.2.circlepath" : "photo.on.rectangle.angled")
                        .font(.system(size: 32))
                        .foregroundColor(selectedImageData != nil ? .white : .secondary.opacity(0.6))
                    Text(selectedImageData != nil ? "点击更换" : (coverURL.isEmpty ? "点击上传封面图" : "点击更换封面图"))
                        .font(.subheadline)
                        .foregroundColor(selectedImageData != nil ? .white : .secondary)
                }
                .padding(8)
                .background(selectedImageData != nil ? Color.black.opacity(0.3) : Color.clear)
                .cornerRadius(8)
            }
            .overlay(RoundedRectangle(cornerRadius: 16)
                .stroke(Color.orange.opacity(0.4), style: StrokeStyle(lineWidth: 1.5, dash: [6])))
        }
    }

    // MARK: - 保存
    private func save() {
        isSaving = true
        errorMessage = nil
        Task {
            do {
                var finalCoverURL = coverURL

                // 1. 有新图片 → 先上传
                if let imgData = selectedImageData {
                    finalCoverURL = try await APIService.shared.uploadImage(imageData: imgData)
                }

                // 2. 更新路线信息（含封面 URL）
                try await APIService.shared.updateRoute(
                    id: route.id,
                    name: name,
                    description: description.isEmpty ? nil : description,
                    difficulty: difficulty,
                    tags: tags,
                    city: city.isEmpty ? nil : city,
                    cover: finalCoverURL.isEmpty ? nil : finalCoverURL,
                    isPublished: isPublished
                )

                await MainActor.run { isSaving = false; dismiss() }
            } catch {
                await MainActor.run { isSaving = false; errorMessage = error.localizedDescription }
            }
        }
    }
}
