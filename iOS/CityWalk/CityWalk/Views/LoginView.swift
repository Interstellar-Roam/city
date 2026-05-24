import SwiftUI

struct LoginView: View {
    @StateObject private var viewModel = AuthViewModel()
    @FocusState private var focusedField: Field?

    enum Field {
        case phone, code
    }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            // 标题
            VStack(spacing: 8) {
                Text("CityWalk")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                Text("发现城市的每一处风景")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }

            // 手机号输入
            VStack(alignment: .leading, spacing: 6) {
                Text("手机号")
                    .font(.caption)
                    .foregroundColor(.secondary)
                TextField("请输入手机号", text: $viewModel.phone)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.roundedBorder)
                    .focused($focusedField, equals: .phone)
            }

            // 验证码输入 + 发送按钮
            VStack(alignment: .leading, spacing: 6) {
                Text("验证码")
                    .font(.caption)
                    .foregroundColor(.secondary)
                HStack(spacing: 12) {
                    TextField("请输入验证码", text: $viewModel.code)
                        .keyboardType(.numberPad)
                        .textFieldStyle(.roundedBorder)
                        .focused($focusedField, equals: .code)

                    Button(action: {
                        Task { await viewModel.sendCode() }
                    }) {
                        Text(viewModel.countdown > 0 ? "\(viewModel.countdown)s" : "发送验证码")
                            .font(.subheadline)
                            .foregroundColor(viewModel.countdown > 0 ? .gray : .blue)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(viewModel.countdown > 0 ? Color.gray.opacity(0.1) : Color.blue.opacity(0.1))
                            .cornerRadius(8)
                    }
                    .disabled(viewModel.countdown > 0 || viewModel.phone.count != 11)
                }
            }

            // 错误提示
            if let error = viewModel.errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }

            // 登录按钮
            Button(action: {
                focusedField = nil
                Task { await viewModel.login() }
            }) {
                Text("登录")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(viewModel.phone.isEmpty || viewModel.code.isEmpty ? Color.gray : Color.blue)
                    .cornerRadius(12)
            }
            .disabled(viewModel.phone.isEmpty || viewModel.code.isEmpty || viewModel.isLoading)

            Spacer()

            // 提示
            Text("未注册手机号将自动创建账号")
                .font(.caption2)
                .foregroundColor(.secondary)
                .padding(.bottom, 32)
        }
        .padding(.horizontal, 32)
        .onAppear {
            focusedField = .phone
        }
    }
}
