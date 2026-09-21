package com.imanunator.wallpaparr

import android.content.ContentProvider
import android.content.ContentValues
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import tv.projectivy.plugin.wallpaperprovider.api.WallpaperProviderContract

class WallpaperProvider : ContentProvider() {
    override fun onCreate(): Boolean = true

    override fun query(
        uri: Uri,
        projection: Array<out String>?,
        selection: String?,
        selectionArgs: Array<out String>?,
        sortOrder: String?,
    ): Cursor? {
        val ctx = context ?: return null
        PreferencesManager.init(ctx.applicationContext)
        val event = uri.getQueryParameter("event")
        val isIdle = uri.getBooleanQueryParameter("isIdle", false)
        if (event == "LAUNCHER_IDLE_MODE_CHANGED" && !isIdle && PreferencesManager.refreshOnIdleExit) {
            forceRefresh(ctx)
        }
        return null
    }

    override fun getType(uri: Uri): String? = null
    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = 0
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?): Int = 0

    companion object {
        fun forceRefresh(context: android.content.Context) {
            WallpaperSession.invalidate()
            val uuid = context.getString(R.string.plugin_uuid)
            context.sendBroadcast(
                Intent(WallpaperProviderContract.ACTION_WALLPAPER_PROVIDER_UPDATED).apply {
                    `package` = SettingsActivity.PROJECTIVY
                    putExtra(WallpaperProviderContract.EXTRA_PROVIDER_ID, uuid)
                    putExtra(
                        WallpaperProviderContract.EXTRA_UPDATE_REASON,
                        WallpaperProviderContract.UpdateReason.DATA_CHANGED,
                    )
                }
            )
        }
    }
}
