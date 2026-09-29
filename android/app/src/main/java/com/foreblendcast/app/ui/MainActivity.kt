package com.foreblendcast.app.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.foreblendcast.app.ui.components.ExerciseBanner
import com.foreblendcast.app.ui.screens.BlenderScreen
import com.foreblendcast.app.ui.screens.CopilotScreen
import com.foreblendcast.app.ui.screens.DistrictDetailScreen
import com.foreblendcast.app.ui.screens.DistrictsScreen
import com.foreblendcast.app.ui.screens.EvaluationScreen
import com.foreblendcast.app.ui.screens.HomeScreen
import com.foreblendcast.app.ui.screens.ReplayScreen
import com.foreblendcast.app.ui.screens.SettingsScreen
import com.foreblendcast.app.ui.theme.ForeBlendCastTheme
import java.net.URLEncoder

object Routes {
    const val HOME = "home"
    const val DISTRICTS = "districts"
    const val BLENDER = "blender"
    const val EVALUATION = "evaluation"
    const val COPILOT = "copilot?q={q}"
    const val REPLAY = "replay"
    const val SETTINGS = "settings"
    const val DISTRICT = "district/{id}"

    fun district(id: String) = "district/" + URLEncoder.encode(id, "UTF-8")
    fun copilot(question: String? = null) = if (question.isNullOrBlank()) "copilot" else "copilot?q=" + URLEncoder.encode(question, "UTF-8")
}

private data class Tab(val route: String, val label: String, val icon: ImageVector)

private val TABS = listOf(
    Tab(Routes.HOME, "Map", Icons.Filled.Home),
    Tab(Routes.DISTRICTS, "Districts", Icons.Filled.List),
    Tab(Routes.BLENDER, "Blender", Icons.Filled.Menu),
    Tab(Routes.EVALUATION, "Evaluate", Icons.Filled.Star),
    Tab("copilot", "Copilot", Icons.Filled.Send),
)

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            ForeBlendCastTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    AppRoot(vm)
                }
            }
        }
    }
}

@Composable
fun AppRoot(vm: AppViewModel) {
    val nav = rememberNavController()
    val backStack by nav.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val showBar = currentRoute != null && (currentRoute in setOf(Routes.HOME, Routes.DISTRICTS, Routes.BLENDER, Routes.EVALUATION) || currentRoute.startsWith("copilot"))

    Scaffold(
        bottomBar = { if (showBar) BottomBar(nav, currentRoute) },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize()) {
            ExerciseBanner()
            NavHost(nav, startDestination = Routes.HOME, modifier = Modifier.fillMaxSize()) {
                composable(Routes.HOME) {
                    HomeScreen(vm, onOpenDistrict = { nav.navigate(Routes.district(it)) }, onOpenReplay = { nav.navigate(Routes.REPLAY) }, onOpenSettings = { nav.navigate(Routes.SETTINGS) })
                }
                composable(Routes.DISTRICTS) { DistrictsScreen(vm, onOpenDistrict = { nav.navigate(Routes.district(it)) }) }
                composable(Routes.BLENDER) { BlenderScreen(vm, onOpenDistrict = { nav.navigate(Routes.district(it)) }) }
                composable(Routes.EVALUATION) { EvaluationScreen(vm) }
                composable(Routes.COPILOT, arguments = listOf(navArgument("q") { type = NavType.StringType; nullable = true; defaultValue = null })) { entry ->
                    CopilotScreen(vm, initialQuestion = entry.arguments?.getString("q"))
                }
                composable(Routes.REPLAY) { ReplayScreen(vm, onBack = { nav.popBackStack() }) }
                composable(Routes.SETTINGS) { SettingsScreen(vm, onBack = { nav.popBackStack() }) }
                composable(Routes.DISTRICT, arguments = listOf(navArgument("id") { type = NavType.StringType })) { entry ->
                    val id = java.net.URLDecoder.decode(entry.arguments?.getString("id") ?: "", "UTF-8")
                    DistrictDetailScreen(
                        vm, id,
                        onBack = { nav.popBackStack() },
                        onAskCopilot = { q -> nav.navigate(Routes.copilot(q)) },
                        onOpenBlender = { nav.navigate(Routes.BLENDER) { launchSingleTop = true } },
                    )
                }
            }
        }
    }
}

@Composable
private fun BottomBar(nav: NavHostController, currentRoute: String?) {
    NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
        TABS.forEach { tab ->
            val selected = currentRoute == tab.route || (tab.route == "copilot" && currentRoute?.startsWith("copilot") == true)
            NavigationBarItem(
                selected = selected,
                onClick = {
                    nav.navigate(tab.route) {
                        popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
                icon = { Icon(tab.icon, contentDescription = tab.label) },
                label = { Text(tab.label) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                ),
            )
        }
    }
}
