[app]
title = OKX Quant Station
package.name = okxquant
package.domain = org.quant.okx
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,enc,bin
version = 1.0.0
requirements = python3,kivy==2.3.1,openssl,cryptography,ccxt,requests,urllib3,certifi,charset-normalizer,idna
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
