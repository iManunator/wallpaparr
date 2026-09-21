package com.imanunator.wallpaparr

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class WallpaperEventReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == "tv.projectivy.launcher.action.REFRESH_WALLPAPER") {
            WallpaperProvider.forceRefresh(context)
        }
    }
}
