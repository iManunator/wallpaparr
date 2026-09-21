package com.imanunator.wallpaparr

import android.os.Bundle
import androidx.leanback.app.GuidedStepSupportFragment
import androidx.leanback.widget.GuidanceStylist
import androidx.leanback.widget.GuidedAction
import com.imanunator.wallpaparr.core.ClientIntents
import com.imanunator.wallpaparr.core.PluginSettingsCopy

/**
 * Root settings screen: the handful of things almost everyone touches
 * (server URL, primary layout, motion preference, opening client).
 * Everything else lives one step deeper, in [AdvancedSettingsFragment].
 */
class SettingsFragment : BaseGuidedSettingsFragment() {
    override fun onCreateGuidance(savedInstanceState: Bundle?): GuidanceStylist.Guidance {
        return GuidanceStylist.Guidance(
            getString(R.string.plugin_name),
            getString(R.string.plugin_description),
            getString(R.string.settings),
            requireContext().getDrawable(R.drawable.ic_plugin),
        )
    }

    override fun onCreateActions(actions: MutableList<GuidedAction>, savedInstanceState: Bundle?) {
        PreferencesManager.init(requireContext())

        actions += header(ID_HDR_CONNECTION, PluginSettingsCopy.CONNECTION)
        actions += editable(ID_SERVER, PluginSettingsCopy.SERVER, PreferencesManager.serverUrl)

        actions += header(ID_HDR_LAYOUTS, PluginSettingsCopy.LAYOUTS)
        actions += editable(ID_LAYOUT, PluginSettingsCopy.PRIMARY_LAYOUT, PreferencesManager.selectedLayout)

        actions += header(ID_HDR_MOTION, PluginSettingsCopy.MOTION)
        actions += checkbox(
            ID_MOTION,
            PluginSettingsCopy.PREFER_MOTION,
            PreferencesManager.preferMotion,
        )

        actions += header(ID_HDR_HOME, PluginSettingsCopy.HOME)
        val selectedClient = ClientIntents.SUPPORTED.firstOrNull {
            it.packageName == PreferencesManager.preferredClient
        }
        actions += listAction(
            ID_CLIENT,
            PluginSettingsCopy.CLIENT.title,
            selectedClient?.name ?: PreferencesManager.preferredClient,
            ClientIntents.SUPPORTED.map { it.name to it.help },
        )

        actions += GuidedAction.Builder(context)
            .id(ID_ADVANCED)
            .title(PluginSettingsCopy.ADVANCED.title)
            .description(PluginSettingsCopy.ADVANCED.hint)
            .multilineDescription(true)
            .build()
    }

    override fun onGuidedActionClicked(action: GuidedAction) {
        when (action.id) {
            ID_MOTION -> {
                PreferencesManager.preferMotion = action.isChecked
                (activity as? SettingsActivity)?.requestWallpaperUpdate()
            }
            ID_ADVANCED -> GuidedStepSupportFragment.add(parentFragmentManager, AdvancedSettingsFragment())
        }
    }

    override fun onGuidedActionEditedAndProceed(action: GuidedAction): Long {
        val text = action.editDescription?.toString()
            ?: action.description?.toString().orEmpty()
        when (action.id) {
            ID_SERVER -> PreferencesManager.serverUrl = text
            ID_LAYOUT -> PreferencesManager.selectedLayout = text
        }
        (activity as? SettingsActivity)?.requestWallpaperUpdate()
        return super.onGuidedActionEditedAndProceed(action)
    }

    override fun onSubGuidedActionClicked(action: GuidedAction): Boolean {
        val parentId = action.id / SUB_STRIDE
        val index = (action.id % SUB_STRIDE).toInt()
        val selectedLabel = when (parentId) {
            ID_CLIENT -> {
                val client = ClientIntents.at(index)
                if (client != null) {
                    PreferencesManager.preferredClient = client.packageName
                    client.name
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
        private const val ID_SERVER = 1L
        private const val ID_LAYOUT = 2L
        private const val ID_MOTION = 4L
        private const val ID_CLIENT = 9L
        private const val ID_ADVANCED = 20L
        private const val ID_HDR_CONNECTION = 1001L
        private const val ID_HDR_LAYOUTS = 1002L
        private const val ID_HDR_MOTION = 1006L
        private const val ID_HDR_HOME = 1007L
    }
}
