package com.imanunator.wallpaparr

import androidx.leanback.app.GuidedStepSupportFragment
import androidx.leanback.widget.GuidedAction
import com.imanunator.wallpaparr.core.SettingCopy

/** Shared GuidedAction builders for [SettingsFragment] and [AdvancedSettingsFragment]. */
abstract class BaseGuidedSettingsFragment : GuidedStepSupportFragment() {
    protected fun header(id: Long, copy: SettingCopy) =
        GuidedAction.Builder(context)
            .id(id)
            .title(copy.title)
            .description(copy.hint)
            .infoOnly(true)
            .focusable(false)
            .multilineDescription(true)
            .build()

    protected fun editable(id: Long, copy: SettingCopy, value: String) =
        GuidedAction.Builder(context)
            .id(id)
            .title(copy.title)
            .description(value)
            .editTitle("${copy.title} — ${copy.hint}")
            .editDescription(value)
            .descriptionEditable(true)
            .multilineDescription(true)
            .build()

    protected fun checkbox(id: Long, copy: SettingCopy, checked: Boolean) =
        GuidedAction.Builder(context)
            .id(id)
            .title(copy.title)
            .description(copy.hint)
            .checkSetId(GuidedAction.CHECKBOX_CHECK_SET_ID)
            .checked(checked)
            .multilineDescription(true)
            .build()

    protected fun listAction(
        id: Long,
        title: String,
        value: String,
        options: List<Pair<String, String>>,
    ): GuidedAction {
        val subs = options.mapIndexed { index, (label, help) ->
            GuidedAction.Builder(context)
                .id(id * SUB_STRIDE + index)
                .title(label)
                .description(help)
                .multilineDescription(true)
                .build()
        }
        return GuidedAction.Builder(context)
            .id(id)
            .title(title)
            .description(value)
            .subActions(subs)
            .multilineDescription(true)
            .build()
    }

    companion object {
        const val SUB_STRIDE = 100L
    }
}
