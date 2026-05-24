import Foundation
import Combine

@MainActor
class AuthViewModel: ObservableObject {
    // MARK: - 状态

    @Published var phone: String = ""
    @Published var code: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var isLoggedIn: Bool = false

    // 验证码倒计时
    @Published var countdown: Int = 0
    private var timer: Timer?

    // MARK: - 生命周期

    init() {
        isLoggedIn = TokenStorage.shared.isLoggedIn
    }

    // MARK: - 发送验证码

    func sendCode() async {
        guard phone.count == 11, phone.allSatisfy(\.isNumber) else {
            errorMessage = "请输入正确的11位手机号"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let response = try await AuthService.shared.sendCode(phone: phone)
            if response.code == 0 {
                startCountdown()
            } else {
                errorMessage = response.message
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - 登录

    func login() async {
        guard !phone.isEmpty, !code.isEmpty else {
            errorMessage = "请输入手机号和验证码"
            return
        }

        isLoading = true
        errorMessage = nil

        do {
            let _ = try await AuthService.shared.login(phone: phone, code: code)
            isLoggedIn = true
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - 登出

    func logout() async {
        do {
            try await AuthService.shared.logout()
        } catch {
            print("Logout error: \(error)")
        }
        isLoggedIn = false
    }

    // MARK: - 倒计时

    private func startCountdown() {
        countdown = 60
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self = self else { return }
                if self.countdown > 0 {
                    self.countdown -= 1
                } else {
                    self.timer?.invalidate()
                    self.timer = nil
                }
            }
        }
    }
}
