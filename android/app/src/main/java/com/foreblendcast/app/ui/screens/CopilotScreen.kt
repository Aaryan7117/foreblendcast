package com.foreblendcast.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.foreblendcast.app.data.CopilotResponse
import com.foreblendcast.app.data.LocalInsights
import com.foreblendcast.app.ui.AppViewModel
import com.foreblendcast.app.ui.UiState
import com.foreblendcast.app.ui.components.MarkdownText
import com.foreblendcast.app.ui.theme.Forest
import com.foreblendcast.app.ui.theme.TierOrange
import kotlinx.coroutines.launch

private data class ChatMessage(val role: String, val text: String, val response: CopilotResponse? = null)

private val DEFAULT_SUGGESTIONS = listOf(
    "Show all red alert districts", "Why is Nalbari red?", "What are the blend weights for Kamrup?",
    "LOMO sensitivity for Barpeta", "How accurate is the blend?", "How many people are exposed in Darrang?",
)

/**
 * Grounded forecaster copilot. Server mode (Gemini or deterministic router) when the API is
 * reachable; otherwise a smaller on-device router over the bundled snapshot. Both only report
 * numbers read from results/ and every answer carries the EXERCISE disclaimer.
 */
@Composable
fun CopilotScreen(vm: AppViewModel, initialQuestion: String?) {
    val leadDay by vm.leadDay.collectAsStateWithLifecycle()
    val ladderState by vm.ladder.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    val messages = remember { mutableStateListOf(ChatMessage("system", "I am the **ForeBlendCast Copilot** — a grounded forecasting assistant. I only answer with numbers from the actual blend results and I never invent warnings.")) }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var suggestions by remember { mutableStateOf(DEFAULT_SUGGESTIONS) }
    val listState = rememberLazyListState()

    LaunchedEffect(Unit) {
        vm.ensureEvaluationLoaded()
        val s = vm.repo.copilotSuggestions(leadDay)
        if (s.isNotEmpty()) suggestions = s
    }

    fun ask(q: String) {
        val question = q.trim()
        if (question.isEmpty() || busy) return
        messages += ChatMessage("user", question)
        input = ""
        busy = true
        scope.launch {
            val server = runCatching { vm.repo.copilot(question, leadDay) }
            val resp = server.getOrElse {
                LocalInsights.copilot(question, vm.currentDistricts(), (ladderState as? UiState.Ready)?.value?.data, leadDay)
            }
            messages += ChatMessage("assistant", resp.answer, resp)
            busy = false
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    var consumedInitial by remember { mutableStateOf(false) }
    LaunchedEffect(initialQuestion) { if (!consumedInitial && !initialQuestion.isNullOrBlank()) { consumedInitial = true; ask(initialQuestion) } }

    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Forecaster copilot", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
                Text("Grounded in results/ · lead D+$leadDay · tool-calling, not a chatbot", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        LazyColumn(Modifier.weight(1f).fillMaxWidth(), state = listState, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            itemsIndexed(messages) { _, m -> Bubble(m) }
            if (busy) item { Text("Thinking…", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(8.dp)) }
        }
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            suggestions.forEach { s -> AssistChip(onClick = { ask(s) }, label = { Text(s) }) }
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = input, onValueChange = { input = it }, modifier = Modifier.weight(1f), singleLine = true,
                placeholder = { Text("Ask about any district forecast…") }, shape = RoundedCornerShape(24.dp),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send), keyboardActions = KeyboardActions(onSend = { ask(input) }),
            )
            Spacer(Modifier.width(6.dp))
            IconButton(onClick = { ask(input) }, enabled = !busy && input.isNotBlank()) { Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = Forest) }
        }
    }
}

@Composable
private fun Bubble(m: ChatMessage) {
    val isUser = m.role == "user"
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        Column(
            Modifier
                .widthIn(max = 340.dp)
                .clip(RoundedCornerShape(topStart = 14.dp, topEnd = 14.dp, bottomStart = if (isUser) 14.dp else 4.dp, bottomEnd = if (isUser) 4.dp else 14.dp))
                .background(when (m.role) { "user" -> Forest; "system" -> MaterialTheme.colorScheme.primaryContainer; else -> MaterialTheme.colorScheme.surface })
                .padding(12.dp),
        ) {
            if (isUser) Text(m.text, color = Color.White, style = MaterialTheme.typography.bodyMedium) else MarkdownText(m.text)
            val r = m.response
            if (r != null) {
                Spacer(Modifier.height(6.dp))
                if (r.sources.isNotEmpty()) Text("Sources: ${r.sources.joinToString(", ")}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Tag(r.mode.ifBlank { "server" })
                    if (!r.intent_detected.isNullOrBlank()) Tag("tool:${r.intent_detected}")
                    if (r.districts_matched.isNotEmpty()) Tag("match:${r.districts_matched.joinToString(",")}")
                }
                if (r.disclaimer.isNotBlank() && !r.answer.contains("EXERCISE")) Text(r.disclaimer, style = MaterialTheme.typography.labelSmall, color = TierOrange, modifier = Modifier.padding(top = 4.dp))
            }
        }
    }
}

@Composable
private fun Tag(text: String) {
    Box(Modifier.clip(RoundedCornerShape(4.dp)).background(MaterialTheme.colorScheme.surfaceVariant).padding(horizontal = 5.dp, vertical = 2.dp)) {
        Text(text, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
