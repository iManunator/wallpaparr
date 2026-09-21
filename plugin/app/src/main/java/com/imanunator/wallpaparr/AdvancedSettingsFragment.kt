package com.imanunator.wallpaparr

import android.os.Bundle
import androidx.leanback.widget.GuidanceStylist
import androidx.leanback.widget.GuidedAction
import com.imanunator.wallpaparr.core.PluginSettingsCopy
import com.imanunator.wallpaparr.core.WallpaperPickModes

/**
 * Everything that isn't on the root [SettingsFragment]: secondary/third
 * layout, pick mode, filters, mix controls, and a few less-common toggles.
 */
class AdvancedSettingsFragment : BaseGuidedSettingsFragment() {
    override fun onCreateGuidance(savedInstanceState: Bundle?): GuidanceStylist.Guidance {
        return GuidanceStylist.Guidance(
            PluginSettingsCopy.ADVANCED.title,
            PluginSettingsCopy.ADVANCED.hint,
            getString(R.string.settings),
            requireContext().getDrawable(R.drawable.ic_plugin),
        )
    }

    override fun onCreateActions(actions: MutableList<GuidedAction>, savedInstanceState: Bundle?) {
        PreferencesManager.init(requireContext())

        actions += header(ID_HDR_LAYOUTS, PluginSettingsCopy.LAYOUTS)
        actions += editable(ID_SECONDARY, PluginSettingsCopy.SECONDARY_LAYOUT, PreferencesManager.secondaryLayout)
        actions += editable(ID_THIRD, PluginSettingsCopy.THIRD_LAYOUT, PreferencesManager.thirdLayout)

        actions += header(ID_HDR_PICK, PluginSettingsCopy.WHAT_TO_SHOW)
        val selectedMode = WallpaperPickModes.byId(PreferencesManager.wallpaperPickMode)
        actions += listAction(
            ID_PICK,
            PluginSettingsCopy.PICK_MODE.title,
            selectedMode?.label ?: WallpaperPickModes.labelFor(PreferencesManager.wallpaperPickMode),
            WallpaperPickModes.ALL.map { it.label to "${it.group} · ${it.help}" },
        )

        actions += header(ID_HDR_FILTERS, PluginSettingsCopy.FILTERS)
        actions += editable(ID_GENRE, PluginSettingsCopy.GENRE, PreferencesManager.genreFilter)
        actions += editable(ID_AGE, PluginSettingsCopy.AGE, PreferencesManager.ageFilter)
        actions += editable(ID_YEAR, PluginSettingsCopy.YEAR, PreferencesManager.yearFilter)
        actions += editable(ID_MIN_RATING, PluginSettingsCopy.MIN_RATING, PreferencesManager.minRating.toString())
        actions += editable(ID_MAX_RATING, PluginSettingsCopy.MAX_RATING, PreferencesManager.maxRating.toString())

        actions += header(ID_HDR_MIX, PluginSettingsCopy.MIX)
        actions += editable(ID_MIX, PluginSettingsCopy.MIX_RATIO, PreferencesManager.mixRatio.toString())
        actions += editable(ID_RECENT, PluginSettingsCopy.RECENT_YEARS, PreferencesManager.recentYears.toString())
        actions += editable(ID_EXCLUDE, PluginSettingsCopy.EXCLUDE, PreferencesManager.excludeDepth.toString())

        actions += header(ID_HDR_MOTION, PluginSettingsCopy.MOTION)
        actions += checkbox(
            ID_FALLBACK,
            PluginSettingsCopy.FALLBACK_STILL,
            PreferencesManager.fallbackStill,
        )

        actions += header(ID_HDR_HOME, PluginSettingsCopy.HOME)
        actions += checkbox(
            ID_IDLE,
            PluginSettingsCopy.IDLE,
            PreferencesManager.refreshOnIdleExit,
        )
        actions += checkbox(
            ID_SEERR_BROWSER,
            PluginSettingsCopy.SEERR_BROWSER_FALLBACK,
            PreferencesManager.seerrOpensInBrowser,
        )
    }

    override fun onGuidedActionClicked(action: GuidedAction) {
        when (action.id) {
            ID_FALLBACK -> PreferencesManager.fallbackStill = action.isChecked
            ID_IDLE -> PreferencesManager.refreshOnIdleExit = action.isChecked
            ID_SEERR_BROWSER -> PreferencesManager.seerrOpensInBrowser = action.isChecked
            else -> return
        }
        (activity as? SettingsActivity)?.requestWallpaperUpdate()
    }

    override fun onGuidedActionEditedAndProceed(action: GuidedAction): Long {
        val text = action.editDescription?.toString()
            ?: action.description?.toString().orEmpty()
        when (action.id) {
            ID_SECONDARY -> PreferencesManager.secondaryLayout = text
            ID_THIRD -> PreferencesManager.thirdLayout = text
            ID_GENRE -> PreferencesManager.genreFilter = text
            ID_AGE -> PreferencesManager.ageFilter = text
            ID_YEAR -> PreferencesManager.yearFilter = text
            ID_MIN_RATING -> PreferencesManager.minRating = text.toFloatOrNull() ?: 0f
            ID_MAX_RATING -> PreferencesManager.maxRating = text.toFloatOrNull() ?: 10f
            ID_MIX -> PreferencesManager.mixRatio = text.toIntOrNull()?.coerceIn(0, 100) ?: 30
            ID_RECENT -> PreferencesManager.recentYears = text.toIntOrNull()?.coerceIn(1, 50) ?: 3
            ID_EXCLUDE -> PreferencesManager.excludeDepth = text.toIntOrNull()?.coerceIn(1, 50) ?: 5
        }
        (activity as? SettingsActivity)?.requestWallpaperUpdate()
        return super.onGuidedActionEditedAndProceed(action)
    }

    override fun onSubGuidedActionClicked(action: GuidedAction): Boolean {
        val parentId = action.id / SUB_STRIDE
        val index = (action.id % SUB_STRIDE).toInt()
        val selectedLabel = when (parentId) {
            ID_PICK -> {
                val mode = WallpaperPickModes.at(index)
                if (mode != null) {
                    PreferencesManager.wallpaperPickMode = mode.id
                    mode.label
                } else {
                    action.title?.toString().orEmpty()
                }
            }
            else -> action.title?.toString().orEmpty()
        }
        val parentPos = selectedActionPosition
        if (parentPos >= 0) {
            val parent = actions.get(parentPos) as? GuidedAction
            if (parent != null) {
                parent.description = selectedLabel
                notifyActionChanged(parentPos)
            }
        }
        (activity as? SettingsActivity)?.requestWallpaperUpdate()
        return true
    }

    companion object {
        private const val ID_SECONDARY = 5L
        private const val ID_THIRD = 11L
        private const val ID_PICK = 3L
        private const val ID_GENRE = 6L
        private const val ID_AGE = 7L
        private const val ID_YEAR = 8L
        private const val ID_MIN_RATING = 15L
        private const val ID_MAX_RATING = 16L
        private const val ID_MIX = 12L
        private const val ID_RECENT = 13L
        private const val ID_EXCLUDE = 14L
        private const val ID_FALLBACK = 17L
        private const val ID_IDLE = 10L
        private const val ID_SEERR_BROWSER = 18L
        private const val ID_HDR_LAYOUTS = 1002L
        private const val ID_HDR_PICK = 1003L
        private const val ID_HDR_FILTERS = 1004L
        private const val ID_HDR_MIX = 1005L
        private const val ID_HDR_MOTION = 1006L
        private const val ID_HDR_HOME = 1007L
    }
}
