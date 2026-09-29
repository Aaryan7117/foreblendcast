package com.foreblendcast.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.BuildConfig
import com.foreblendcast.app.data.Settings
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.components.SectionCard
import com.foreblendcast.app.ui.theme.TierGreen
import com.foreblendcast.app.ui.theme.TierRed
import kotlinx.coroutines.launch

@Composable
fun SettingsScreen(vm: AppViewModel, onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    val baseUrl by vm.settings.baseUrl.collectAsStateWithLifecycle()
    val phone by vm.settings.phone.collectAsStateWithLifecycle()
    val language by vm.settings.language.collectAsStateWithLifecycle()
    val health by vm.connection.collectAsStateWithLifecycle()
    val lastError by vm.repo.lastError.collectAsStateWithLifecycle()
    var url by remember(baseUrl) { mutableStateOf(baseUrl) }
    var phoneEdit by remember(phone) { mutableStateOf(phone) }
    var testResult by remember { mutableStateOf<String?>(null) }
    var capXml by remember { mutableStateOf<String?>(null) }
    val leadDay by vm.leadDay.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
            Text("Settings & connection", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        }
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            SectionCard("API server", subtitle = "FastAPI from the repo: scripts/run_api.ps1 (binds 0.0.0.0:8000)") {
                OutlinedTextField(value = url, onValueChange = { url = it }, label = { Text("Base URL") }, singleLine = true, modifier = Modifier.fillMaxWidth(), textStyle = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace))
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    AssistChip(onClick = { url = "http://10.0.2.2:8000" }, label = { Text("Emulator") })
                    AssistChip(onClick = { url = BuildConfig.DEFAULT_API_BASE_URL }, label = { Text("Build default") })
                }
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        vm.onServerUrlChanged(url)
                        testResult = "Testing…"
                        scope.launch {
                            testResult = vm.repo.checkConnection().fold(
                                { h -> "Connected · API ${h.version} · leads ${h.available_lead_days} · cycle ${h.cycle} · LLM copilot ${if (h.copilot_llm) "on" else "off"} · SMS gateway ${if (h.sms_gateway_configured) "configured" else "mock"}" },
                                { e -> "Failed: ${e.message}" },
                            )
                        }
                    }, modifier = Modifier.weight(1f)) { Text("Save & test") }
                }
                val ok = health != null
                Text(
                    testResult ?: if (ok) "Connected to ${Settings.normalizeUrl(baseUrl)}" else "Not connected — using the bundled snapshot" + (lastError?.let { " ($it)" } ?: ""),
                    style = MaterialTheme.typography.bodySmall, color = if ((testResult?.startsWith("Failed") == true) || (!ok && testResult == null)) TierRed else TierGreen, modifier = Modifier.padding(top = 6.dp),
                )
                Text("Phone on the same Wi-Fi: use the LAN IP printed by run_api.ps1 (e.g. http://192.168.1.20:8000). Emulator: 10.0.2.2 reaches the host.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(top = 4.dp))
            }

            SectionCard("SMS demo defaults") {
                OutlinedTextField(value = phoneEdit, onValueChange = { phoneEdit = it; vm.settings.setPhone(it) }, label = { Text("Default phone") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Settings.LANGUAGES.forEach { (code, label) -> FilterChip(selected = language == code, onClick = { vm.settings.setLanguage(code) }, label = { Text(label) }) }
                }
            }

            SectionCard("CAP 1.2 feed", subtitle = "What NDMA SACHET would ingest — red/orange districts for D+$leadDay") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { scope.launch { capXml = runCatching { vm.repo.capFeedXml(leadDay) }.getOrElse { "Failed: ${it.message}" } } }) { Text("Fetch XML") }
                }
                Text(vm.repo.capFeedUrl(leadDay), style = MaterialTheme.typography.labelSmall, fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (capXml != null) Text(capXml!!.take(4000), style = MaterialTheme.typography.labelSmall, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(top = 6.dp))
            }

            SectionCard("About") {
                Text("ForeBlendCast — SIH26081. Calibrated, context-aware blend of ECMWF IFS HRES, IFS ENS mean and DeepMind GraphCast rainfall for 735 Indian districts, verified against ERA5 on held-out years.", style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(6.dp))
                Text("App ${BuildConfig.VERSION_NAME} · bundled snapshot for lead days 1, 3, 5 · everything is an EXERCISE output, not an IMD warning.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Spacer(Modifier.height(12.dp))
        }
    }
}
