package com.imanunator.wallpaparr.core

data class StatusRequest(
    val layout: String,
    val genre: String? = null,
    val ageRating: String? = null,
    val minYear: String? = null,
    val maxYear: String? = null,
    val minRating: Float? = null,
    val maxRating: Float? = null,
    val sort: String? = null,
    val pool: String? = null,
    val exclude: String? = null,
    val profile: String? = null,
    val queue: String? = null,
) {
    fun toQueryMap(): Map<String, String> {
        val out = linkedMapOf("layout" to layout)
        genre?.takeIf { it.isNotBlank() }?.let { out["genre"] = it }
        ageRating?.takeIf { it.isNotBlank() }?.let { out["age_rating"] = it }
        minYear?.takeIf { it.isNotBlank() }?.let { out["min_year"] = it }
        maxYear?.takeIf { it.isNotBlank() }?.let { out["max_year"] = it }
        if (minRating != null && minRating > 0f) out["min_rating"] = minRating.toString()
        if (maxRating != null && maxRating < 10f) out["max_rating"] = maxRating.toString()
        sort?.takeIf { it.isNotBlank() }?.let { out["sort"] = it }
        pool?.takeIf { it.isNotBlank() }?.let { out["pool"] = it }
        exclude?.takeIf { it.isNotBlank() }?.let { out["exclude"] = it }
        profile?.takeIf { it.isNotBlank() }?.let { out["profile"] = it }
        queue?.takeIf { it.isNotBlank() }?.let { out["queue"] = it }
        return out
    }
}
