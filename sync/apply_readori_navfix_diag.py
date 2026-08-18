from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one match, found {count}\nneedle:\n{old[:1200]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched {relative}")


replace_once(
    "Readori/Core/Theme/AppThemeManager.swift",
    '''    private let transparentNavigationAppearance: UINavigationBarAppearance = {
        let appearance = UINavigationBarAppearance()
        appearance.configureWithTransparentBackground()
        appearance.backgroundColor = .clear
        appearance.backgroundEffect = nil
        appearance.shadowColor = .clear
        return appearance
    }()
''',
    '''    /// NavigationStack creates the destination controller before the pushed
    /// SwiftUI wallpaper background has completed its first layout pass. A fully
    /// transparent UINavigationBar therefore exposed the root wallpaper crop for
    /// the first transition frames. Install a deterministic readability veil at
    /// the UIKit layer so the top safe-area is stable from frame zero.
    private func wallpaperNavigationAppearance() -> UINavigationBarAppearance {
        let appearance = UINavigationBarAppearance()
        appearance.configureWithTransparentBackground()
        let base: UIColor = prefersDarkTextOnWallpaper ? .white : .black
        let alpha: CGFloat = UIAccessibility.isReduceTransparencyEnabled ? 1.0 : 0.50
        appearance.backgroundColor = base.withAlphaComponent(alpha)
        appearance.backgroundEffect = nil
        appearance.shadowColor = UIColor.separator.withAlphaComponent(0.18)
        return appearance
    }
''',
)

replace_once(
    "Readori/Core/Theme/AppThemeManager.swift",
    '''                let appearance = wallpaperEnabled ? transparentNavigationAppearance : defaultNavigationAppearance
                nav.navigationBar.standardAppearance = appearance
                nav.navigationBar.scrollEdgeAppearance = appearance
                nav.navigationBar.compactAppearance = appearance
                nav.navigationBar.compactScrollEdgeAppearance = appearance
                nav.navigationBar.isTranslucent = wallpaperEnabled
''',
    '''                let appearance = wallpaperEnabled ? wallpaperNavigationAppearance() : defaultNavigationAppearance
                nav.navigationBar.standardAppearance = appearance
                nav.navigationBar.scrollEdgeAppearance = appearance
                nav.navigationBar.compactAppearance = appearance
                nav.navigationBar.compactScrollEdgeAppearance = appearance
                nav.navigationBar.isTranslucent = wallpaperEnabled && !UIAccessibility.isReduceTransparencyEnabled
''',
)

replace_once(
    "Readori/UI/Common/ViewExtensions.swift",
    '''        if appThemeManager.hasCustomBackgroundImage {
            // A wallpaper is the page chrome. Painting a system material here
            // recreates the white/black strip users explicitly opted out of.
            content
                .toolbarBackground(Color.clear, for: .navigationBar)
                .toolbarBackground(.hidden, for: .navigationBar)
        } else if reduceTransparency {
''',
    '''        if appThemeManager.hasCustomBackgroundImage {
            // UIKit installs the same veil before the destination hierarchy is
            // mounted. Keeping SwiftUI's navigation background visible prevents
            // a raw/root-wallpaper strip during the push transition.
            let navigationBackground = reduceTransparency
                ? (appThemeManager.prefersDarkTextOnWallpaper ? Color.white : Color.black)
                : appThemeManager.fixedBottomNavigationBackground
            content
                .toolbarBackground(navigationBackground, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
        } else if reduceTransparency {
''',
)

replace_once(
    "Readori/UI/Common/ViewExtensions.swift",
    '''        if appWallpaperSurfaceEnabled, let image = appThemeManager.appBackgroundImage {
            // Reuse the one UIImage decoded by AppThemeManager, but paint it inside
            // every pushed page's own hierarchy. NavigationStack/Form can install
            // an opaque hosting surface between a destination and ContentView on
            // iOS 26; merely setting `.background(Color.clear)` therefore leaves a
            // white page even though the root wallpaper exists underneath.
            // Reassert public UIKit list-cell backgroundConfiguration on the next
            // run loop as well; this also covers destinations that contain an
            // indirectly nested List/Form but forgot the dedicated list modifier.
            content
                .background { ReadoriAppWallpaperBackdrop(image: image) }
                .onAppear {
                    appThemeManager.refreshMountedWallpaperListBackgrounds()
                    DispatchQueue.main.async {
                        appThemeManager.refreshMountedWallpaperListBackgrounds()
                    }
                }
        } else if reduceTransparency {
            content.background(fallback)
        } else {
            content.background { Rectangle().fill(.ultraThinMaterial) }
        }
''',
    '''        if appWallpaperSurfaceEnabled, let image = appThemeManager.appBackgroundImage {
            let navigationBackground = reduceTransparency
                ? (appThemeManager.prefersDarkTextOnWallpaper ? Color.white : Color.black)
                : appThemeManager.fixedBottomNavigationBackground
            content
                .background { ReadoriAppWallpaperBackdrop(image: image) }
                .toolbarBackground(navigationBackground, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
                .onAppear {
                    DiagnosticLogger.shared.log(.info, .navigation, "Adaptive page surface appeared", context: [
                        "wallpaper": "1",
                        "backgroundReady": "1",
                        "pageSurface": "wallpaperBackdrop",
                        "navigationChrome": reduceTransparency ? "opaqueWallpaperVeil" : "wallpaperVeil"
                    ])
                    appThemeManager.refreshMountedWallpaperListBackgrounds()
                    DispatchQueue.main.async {
                        appThemeManager.refreshMountedWallpaperListBackgrounds()
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
                        DiagnosticLogger.shared.log(.debug, .navigation, "Adaptive page surface settled", context: [
                            "wallpaper": appThemeManager.hasCustomBackgroundImage ? "1" : "0",
                            "backgroundReady": appThemeManager.appBackgroundImage == nil ? "0" : "1",
                            "navigationChrome": reduceTransparency ? "opaqueWallpaperVeil" : "wallpaperVeil"
                        ])
                    }
                }
        } else if reduceTransparency {
            content
                .background(fallback)
                .toolbarBackground(fallback, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
                .onAppear {
                    DiagnosticLogger.shared.log(.info, .navigation, "Adaptive page surface appeared", context: [
                        "wallpaper": "0",
                        "backgroundReady": "0",
                        "pageSurface": "opaqueSystem",
                        "navigationChrome": "opaqueSystem"
                    ])
                }
        } else {
            content
                .background { Rectangle().fill(.ultraThinMaterial) }
                .toolbarBackground(.ultraThinMaterial, for: .navigationBar)
                .toolbarBackground(.visible, for: .navigationBar)
                .onAppear {
                    DiagnosticLogger.shared.log(.info, .navigation, "Adaptive page surface appeared", context: [
                        "wallpaper": "0",
                        "backgroundReady": "0",
                        "pageSurface": "ultraThinMaterial",
                        "navigationChrome": "ultraThinMaterial"
                    ])
                }
        }
''',
)

replace_once(
    "Readori/UI/Settings/SettingsView.swift",
    '''    private func logSettingsDestinationAppeared(_ category: PrimaryCategory) {
        DiagnosticLogger.shared.log(.info, .navigation, "Settings destination appeared", context: [
            "category": String(describing: category),
            "wallpaper": appThemeManager.hasCustomBackgroundImage ? "1" : "0"
        ])
    }
''',
    '''    private func logSettingsDestinationAppeared(_ category: PrimaryCategory) {
        DiagnosticLogger.shared.log(.info, .navigation, "Settings destination appeared", context: [
            "category": String(describing: category),
            "wallpaper": appThemeManager.hasCustomBackgroundImage ? "1" : "0",
            "backgroundReady": appThemeManager.appBackgroundImage == nil ? "0" : "1",
            "layout": isSplitLayoutActive ? "split" : "compact",
            "navigationDepth": isSplitLayoutActive ? "0" : "\\(compactPath.count)",
            "navigationChrome": appThemeManager.hasCustomBackgroundImage ? "wallpaperVeil" : "systemMaterial"
        ])
    }
''',
)

replace_once(
    "Readori/Services/TTS/ReadoriAITTSClient.swift",
    '''        try await deviceAuth.authorize(&request, retrying: retryingAuth)

        do {
            let (data, response) = try await TTSNetworkSession.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw TTSProviderError.invalidResponse }
''',
    '''        try await deviceAuth.authorize(&request, retrying: retryingAuth)
        let requestStartedAt = ProcessInfo.processInfo.systemUptime

        do {
            let (data, response) = try await TTSNetworkSession.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw TTSProviderError.invalidResponse }
''',
)

replace_once(
    "Readori/Services/TTS/ReadoriAITTSClient.swift",
    '''            guard (200..<300).contains(http.statusCode) else {
                throw Self.providerError(for: http.statusCode, data: data)
            }

            let payload = try TTSHTTPAudioResponseDecoder.decode(
                data: data,
                response: response,
                expectedContentType: "audio/mpeg"
            )
            guard case let .data(audio) = payload, !audio.isEmpty else {
                throw TTSProviderError.emptyAudio
            }
            return ReadoriAITTSResult(
                audio: audio,
                provider: http.value(forHTTPHeaderField: "X-READORI-TTS-PROVIDER") ?? "server"
            )
''',
    '''            let latencyMS = max(0, Int(((ProcessInfo.processInfo.systemUptime - requestStartedAt) * 1_000).rounded()))
            let provider = http.value(forHTTPHeaderField: "X-READORI-TTS-PROVIDER") ?? "server"
            let revision = http.value(forHTTPHeaderField: "X-READORI-TTS-REVISION") ?? "unknown"
            let trace = http.value(forHTTPHeaderField: "CF-Ray")
                ?? http.value(forHTTPHeaderField: "X-Request-ID")
                ?? ""
            let contentType = http.value(forHTTPHeaderField: "Content-Type") ?? ""

            guard (200..<300).contains(http.statusCode) else {
                let workerFailure = Self.workerError(from: data)
                DiagnosticLogger.shared.log(.warning, .network, "AI narration worker response failed", context: [
                    "status": "\\(http.statusCode)",
                    "code": workerFailure.code ?? "HTTP_\\(http.statusCode)",
                    "provider": provider,
                    "workerRevision": revision,
                    "latencyMs": "\\(latencyMS)",
                    "trace": trace,
                    "authRetry": retryingAuth ? "1" : "0"
                ])
                throw Self.providerError(for: http.statusCode, data: data)
            }

            let payload = try TTSHTTPAudioResponseDecoder.decode(
                data: data,
                response: response,
                expectedContentType: "audio/mpeg"
            )
            guard case let .data(audio) = payload, !audio.isEmpty else {
                throw TTSProviderError.emptyAudio
            }
            DiagnosticLogger.shared.log(.info, .network, "AI narration worker audio received", context: [
                "status": "\\(http.statusCode)",
                "provider": provider,
                "workerRevision": revision,
                "bytes": "\\(audio.count)",
                "latencyMs": "\\(latencyMS)",
                "contentType": contentType,
                "trace": trace,
                "authRetry": retryingAuth ? "1" : "0"
            ])
            return ReadoriAITTSResult(audio: audio, provider: provider)
''',
)

replace_once(
    "Readori/Services/TTSService.swift",
    '''        let remainingRanges = sentenceRanges.indices.contains(remainingStart)
            ? Array(sentenceRanges[remainingStart...])
            : []

        // 清空 HTTP 相关状态，切换到系统语音路径继续朗读剩余内容
''',
    '''        let remainingRanges = sentenceRanges.indices.contains(remainingStart)
            ? Array(sentenceRanges[remainingStart...])
            : []

        diagLog(.warning, .general, "TTS fallback to system", ctx: [
            "configuredProvider": config.providerType.rawValue,
            "fromSentence": "\\(remainingStart)",
            "remainingSentences": "\\(remainingSentences.count)",
            "noticeSource": notice == nil ? "default" : "explicit"
        ])

        // 清空 HTTP 相关状态，切换到系统语音路径继续朗读剩余内容
''',
)

replace_once(
    "Readori/Services/TTSService.swift",
    '''            case .aiNarration:
                let payload = try await aiNarrationAudio(at: httpSentenceIndex, sentence: sentence)
                data = payload.data
                // MeloTTS and the self-hosted CosyVoice path do not expose the
''',
    '''            case .aiNarration:
                let payload = try await aiNarrationAudio(at: httpSentenceIndex, sentence: sentence)
                data = payload.data
                diagLog(.info, .general, "AI narration audio resolved", ctx: [
                    "provider": payload.provider,
                    "bytes": "\\(payload.data.count)",
                    "sentence": "\\(httpSentenceIndex)",
                    "mode": config.aiNarrationMode.rawValue
                ])
                // MeloTTS and the self-hosted CosyVoice path do not expose the
''',
)

replace_once(
    "Readori/Services/TTSService.swift",
    '''        httpAudioPlayer = player
        switch state {
''',
    '''        httpAudioPlayer = player
        if httpSentenceIndex == 0 {
            diagLog(.info, .general, "TTS online audio player ready", ctx: [
                "configuredProvider": config.providerType.rawValue,
                "sentence": "\\(httpSentenceIndex)",
                "bytes": "\\(data.count)",
                "durationMs": "\\(max(0, Int((player.duration * 1_000).rounded())))",
                "rateOverride": playbackRateOverride.map { String(format: "%.2f", $0) } ?? "none"
            ])
        }
        switch state {
''',
)

replace_once(
    "Readori/Supporting/Info.plist",
    '''    <key>READORI_SOURCE_PATCH_LEVEL</key>
    <string>build26-compilefix</string>
''',
    '''    <key>READORI_SOURCE_PATCH_LEVEL</key>
    <string>nav-transition-diag-v1-20260818</string>
''',
)

print("all source patches applied")
