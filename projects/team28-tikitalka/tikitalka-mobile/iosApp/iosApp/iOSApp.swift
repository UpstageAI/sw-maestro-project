import SwiftUI
import ComposeApp

@main
struct iOSApp: App {
    init() {
        MainViewControllerKt.startKoinIos(
            baseUrl: LocalConfig.baseUrl,
            footballApiKey: LocalConfig.footballApiKey
        )
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}