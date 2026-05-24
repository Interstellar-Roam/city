import SwiftUI

struct LoginView: View {
    @ObservedObject var viewModel: AuthViewModel
    @FocusState private var focusedField: Field?

    enum Field {
        case phone, code
    }

    var body: some View {
        ZStack {
            // 背景层
            Color(.systemGroupedBackground)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()
                    .frame(height: 60)

                // MARK: - Logo & 标题
                VStack(spacing: 16) {
                    // App 图标
                    ZStack {
                        RoundedRectangle(cornerRadius: 24)
                            .fill(
                                LinearGradient(
                                    colors: [.orange, .orange.opacity(0.7)],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 72, height: 72)

                        Image(systemName: "figure.walk")
                            .font(.system(size: 36, weight: .semibold))
                            .foregroundColor(.white)
                    }
                    .shadow(color: .orange.opacity(0.3), radius: 12, y: 4)

                    Text("CityWalk")
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundColor(.primary)

                    Text("发现城市的每一处风景")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()
                    .frame(height: 48)

                // MARK: - 输入区域
                VStack(spacing: 20) {
                    // 手机号
                    HStack(spacing: 10) {
                        Image(systemName: "phone.fill")
                            .font(.system(size: 16))
                            .foregroundColor(focusedField == .phone ? .orange : .secondary.opacity(0.5))
                            .frame(width: 20)
                            .animation(.easeInOut(duration: 0.2), value: focusedField)

                        Text("+86")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(.secondary)
                            .padding(.trailing, 4)

                        Rectangle()
                            .frame(width: 1, height: 16)
                            .foregroundColor(.secondary.opacity(0.2))

                        TextField("请输入手机号", text: $viewModel.phone)
                            .keyboardType(.numberPad)
                            .font(.system(size: 16))
                            .focused($focusedField, equals: .phone)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                    .background(
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color(.systemBackground))
                            .shadow(color: focusedField == .phone ? .orange.opacity(0.08) : .clear, radius: 8, y: 2)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .stroke(focusedField == .phone ? Color.orange.opacity(0.4) : Color.clear, lineWidth: 1.5)
                    )
                    .animation(.easeInOut(duration: 0.2), value: focusedField)

                    // 验证码
                    HStack(spacing: 10) {
                        inputField(
                            icon: "lock.fill",
                            placeholder: "请输入验证码",
                            text: $viewModel.code,
                            keyboardType: .numberPad,
                            field: .code
                        )

                        // 发送验证码按钮
                        Button(action: {
                            Task { await viewModel.sendCode() }
                        }) {
                            Text(viewModel.countdown > 0 ? "\(viewModel.countdown)s" : "获取验证码")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundColor(
                                    viewModel.phone.count == 11 && viewModel.countdown == 0
                                        ? .orange : .secondary
                                )
                                .padding(.horizontal, 14)
                                .padding(.vertical, 14)
                                .frame(minWidth: 90)
                                .background(
                                    RoundedRectangle(cornerRadius: 14)
                                        .fill(Color(.systemBackground))
                                        .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
                                )
                        }
                        .disabled(viewModel.countdown > 0 || viewModel.phone.count != 11)
                    }
                }

                // 错误提示
                if let error = viewModel.errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .padding(.top, 12)
                        .transition(.opacity)
                }

                Spacer()
                    .frame(height: 32)

                // MARK: - 登录按钮
                Button(action: {
                    focusedField = nil
                    Task { await viewModel.login() }
                }) {
                    HStack(spacing: 8) {
                        if viewModel.isLoading {
                            ProgressView()
                                .tint(.white)
                        }
                        Text("登录")
                            .font(.system(size: 17, weight: .semibold))
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(
                                viewModel.phone.isEmpty || viewModel.code.isEmpty
                                    ? AnyShapeStyle(Color.gray.opacity(0.35))
                                    : AnyShapeStyle(
                                        LinearGradient(
                                            colors: [.orange, .orange.opacity(0.85)],
                                            startPoint: .leading,
                                            endPoint: .trailing
                                        )
                                    )
                            )
                    )
                }
                .disabled(viewModel.phone.isEmpty || viewModel.code.isEmpty || viewModel.isLoading)
                .animation(.easeInOut(duration: 0.2), value: viewModel.phone.isEmpty || viewModel.code.isEmpty)

                Spacer()
                    .frame(height: 20)

                // 底部提示
                HStack(spacing: 4) {
                    Image(systemName: "checkmark.shield.fill")
                        .font(.caption2)
                        .foregroundColor(.secondary.opacity(0.6))
                    Text("未注册手机号将自动创建账号")
                        .font(.caption2)
                        .foregroundColor(.secondary.opacity(0.6))
                }

                Spacer()
            }
            .padding(.horizontal, 28)
        }
        .onAppear {
            focusedField = .phone
        }
        .onChange(of: viewModel.code) { code in
            if code.count == 6, !viewModel.phone.isEmpty {
                focusedField = nil
                Task { await viewModel.login() }
            }
        }
        .animation(.easeInOut(duration: 0.3), value: viewModel.errorMessage)
    }

    // MARK: - 输入框组件
    private func inputField(
        icon: String,
        placeholder: String,
        text: Binding<String>,
        keyboardType: UIKeyboardType,
        field: Field
    ) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(focusedField == field ? .orange : .secondary.opacity(0.5))
                .frame(width: 20)
                .animation(.easeInOut(duration: 0.2), value: focusedField)

            TextField(placeholder, text: text)
                .keyboardType(keyboardType)
                .font(.system(size: 16))
                .focused($focusedField, equals: field)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(.systemBackground))
                .shadow(color: focusedField == field ? .orange.opacity(0.08) : .clear, radius: 8, y: 2)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(focusedField == field ? Color.orange.opacity(0.4) : Color.clear, lineWidth: 1.5)
        )
        .animation(.easeInOut(duration: 0.2), value: focusedField)
    }
}
