[app]

# 应用基本信息
title = OKX Pro Quant
package.name = okxquant
package.domain = org.quant.okx
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,txt

version = 1.0.0

# 核心依赖项：彻底剔除引发闪退的 cryptography，保留网络与交易依赖
requirements = python3,kivy,requests,urllib3,certifi,charset-normalizer,idna

# 屏幕方向
orientation = portrait

# 安卓权限（联网权限）
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# 兼容架构：适配你的骁龙 8 至尊版纯 64 位芯片
android.archs = arm64-v8a

# API 级别与环境配置
android.api = 34
android.minapi = 26
android.ndk = 25b
android.accept_sdk_license = True
android.skip_update = False

[buildozer]
log_level = 2
warn_on_root = 1
