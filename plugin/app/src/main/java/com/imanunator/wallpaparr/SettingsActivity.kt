package com.imanunator.wallpaparr

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.fragment.app.FragmentActivity
import androidx.leanback.app.GuidedStepSupportFragment
import tv.projectivy.plugin.wallpaperprovider.api.WallpaperProviderContract

class SettingsActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PreferencesManager.init(applicationContext)
        if (!packageManager.isInstalled(PROJECTIVY)) {
            Toast.makeText(this, R.string.projectivy_not_installed, Toast.LENGTH_LONG).show()
        }
        if (savedInstanceState == null) {
            GuidedStepSupportFragment.addAsRoot(this, SettingsFragment(), android.R.id.content)
        }
    }

    fun requestWallpaperUpdate() {
        WallpaperSession.invalidate()
        sendBroadcast(
            Intent(WallpaperProviderContract.ACTION_WALLPAPER_PROVIDER_UPDATED).apply {
                `package` = PROJECTIVY
                putExtra(WallpaperProviderContract.EXTRA_PROVIDER_ID, getString(R.string.plugin_uuid))
                putExtra(
                    WallpaperProviderContract.EXTRA_UPDATE_REASON,
                    WallpaperProviderContract.UpdateReason.PREFS_CHANGED,
                )
            }
        )
    }

    private fun PackageManager.isInstalled(pkg: String): Boolean = try {
        getApplicationInfo(pkg, 0)
        true
    } catch (_: Exception) {
        false
    }

    companion object {
        const val PROJECTIVY = "com.spocky.projengmenu"
    }
}
