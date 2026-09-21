package com.imanunator.wallpaparr.core

data class ChosenWallpaper(val uri: String, val isVideo: Boolean)

object MediaChoice {
    /**
     * Projectivy IMAGE vs VIDEO selection.
     * IMAGE = JPEG still. VIDEO = looping MP4 (parallax / Ken Burns).
     *
     * preferMotion: use the clip when [videoUrl] exists.
     * fallbackStill: if we wanted motion but there is no clip, show the JPEG
     * instead of skipping the title (plugin then holds the previous wallpaper).
     */
    fun choose(
        imageUrl: String?,
        videoUrl: String?,
        mediaType: String?,
        preferMotion: Boolean,
        fallbackStill: Boolean = true,
    ): ChosenWallpaper? {
        val hasVideo = !videoUrl.isNullOrBlank() && (
            mediaType.equals("video", ignoreCase = true) ||
                videoUrl.contains(".mp4", ignoreCase = true)
            )
        val hasImage = !imageUrl.isNullOrBlank()
        if (preferMotion && hasVideo) {
            return ChosenWallpaper(videoUrl!!, true)
        }
        if (hasImage && (!preferMotion || fallbackStill)) {
            return ChosenWallpaper(imageUrl!!, false)
        }
        if (hasVideo) {
            return ChosenWallpaper(videoUrl!!, true)
        }
        return null
    }
}
