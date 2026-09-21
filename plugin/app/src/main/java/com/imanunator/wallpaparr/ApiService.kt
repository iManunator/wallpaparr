package com.imanunator.wallpaparr

import retrofit2.Call
import retrofit2.http.GET
import retrofit2.http.Query

data class WallpaperStatus(
    val imageUrl: String?,
    val actionUrl: String?,
    val title: String? = null,
    val path: String? = null,
    val mediaType: String? = null,
    val videoUrl: String? = null,
    val parallaxStyle: String? = null,
    val motionDuration: Float? = null,
    val sort: String? = null,
    val pool: String? = null,
    val layout: String? = null,
)

interface ApiService {
    @GET("/api/wallpaper/status")
    fun getWallpaperStatus(
        @Query("layout") layout: String,
        @Query("genre") genre: String? = null,
        @Query("age_rating") ageRating: String? = null,
        @Query("min_year") minYear: String? = null,
        @Query("max_year") maxYear: String? = null,
        @Query("min_rating") minRating: Float? = null,
        @Query("max_rating") maxRating: Float? = null,
        @Query("sort") sort: String? = null,
        @Query("pool") pool: String? = null,
        @Query("exclude") exclude: String? = null,
        @Query("profile") profile: String? = null,
        @Query("queue") queue: String? = null,
    ): Call<WallpaperStatus>

    @GET("/api/layouts/list")
    fun getLayouts(): Call<List<String>>

    @GET("/api/layouts/with-images")
    fun getLayoutsWithImages(): Call<List<String>>

    @GET("/api/genres/list")
    fun getGenres(): Call<List<String>>

    @GET("/api/ages/list")
    fun getAgeRatings(): Call<List<String>>

    @GET("/api/year/list")
    fun getYears(): Call<List<String>>
}
