package com.foreblendcast.app

import android.app.Application
import com.foreblendcast.app.data.Repository
import com.foreblendcast.app.data.Settings

class ForeBlendCastApp : Application() {
    lateinit var settings: Settings
        private set
    lateinit var repository: Repository
        private set

    override fun onCreate() {
        super.onCreate()
        settings = Settings(this)
        repository = Repository(this, settings)
    }
}
