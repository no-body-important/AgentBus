package com.agentbus.mobile

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.produceState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.documentfile.provider.DocumentFile
import org.json.JSONArray
import org.json.JSONObject

private const val REPO_PREFS = "agentbus_mobile_repo"
private const val REPO_URI_PREF = "repo_tree_uri"

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun RepoScreen() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences(REPO_PREFS, Context.MODE_PRIVATE) }
    var repoTreeUriString by rememberSaveable {
        mutableStateOf(prefs.getString(REPO_URI_PREF, "") ?: "")
    }
    var refreshNonce by remember { mutableIntStateOf(0) }
    var memorySearchQuery by rememberSaveable { mutableStateOf("") }
    var memoryTitle by rememberSaveable { mutableStateOf("") }
    var memorySummary by rememberSaveable { mutableStateOf("") }
    var memoryTags by rememberSaveable { mutableStateOf("android, manual") }
    var memorySourcePath by rememberSaveable { mutableStateOf("android-app") }
    var memoryStatus by rememberSaveable { mutableStateOf("") }
    var selectedMemoryId by rememberSaveable { mutableStateOf("") }

    val pickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocumentTree(),
    ) { uri ->
        if (uri != null) {
            context.contentResolver.takePersistableUriPermission(
                uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION,
            )
            repoTreeUriString = uri.toString()
            prefs.edit().putString(REPO_URI_PREF, repoTreeUriString).apply()
            refreshNonce++
        }
    }

    val repoTreeUri = remember(repoTreeUriString) {
        repoTreeUriString.takeIf { it.isNotBlank() }?.let(Uri::parse)
    }

    val snapshot by produceState(
        initialValue = RepoSnapshot.empty(),
        repoTreeUriString,
        refreshNonce,
    ) {
        value = loadRepoSnapshot(context, repoTreeUri)
    }
    val selectedMemoryEntry = remember(snapshot.memoryEntries, selectedMemoryId) {
        snapshot.memoryEntries.firstOrNull { it.memoryId == selectedMemoryId }
    }
    val selectedMemoryBody by produceState(
        initialValue = "",
        repoTreeUriString,
        selectedMemoryEntry?.notePath,
        refreshNonce,
    ) {
        value = if (repoTreeUri != null && selectedMemoryEntry != null) {
            readMemoryNoteBody(context, repoTreeUri, selectedMemoryEntry.notePath).orEmpty()
        } else {
            ""
        }
    }

    val scrollState = rememberScrollState()
    Column(
        modifier = Modifier
            .padding(20.dp)
            .verticalScroll(scrollState),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        SectionHeader(
            title = "Live Repo",
            subtitle = "Connect a local clone or synced folder and read AgentBus state directly.",
        )
        if (repoTreeUriString.isBlank()) {
            EmptyRepoHint()
        }

        RepoStatusCard(
            snapshot = snapshot,
            repoTreeUriString = repoTreeUriString,
            onPickFolder = { pickerLauncher.launch(repoTreeUri) },
            onRefresh = { refreshNonce++ },
        )

        SummarySection(
            title = "Agent handles",
            subtitle = "Parsed from `agent_bus/config/agents.yaml` or inferred from live task folders.",
            items = snapshot.agentHandles.ifEmpty { listOf("No registry found yet") },
        )
        SummarySection(
            title = "Task buckets",
            subtitle = "Shows the live task folders and file counts.",
            items = snapshot.taskBuckets.ifEmpty { listOf("No task folders found yet") },
        )
        SummarySection(
            title = "Result buckets",
            subtitle = "Shows recent result folders and file counts.",
            items = snapshot.resultBuckets.ifEmpty { listOf("No result folders found yet") },
        )
        SummarySection(
            title = "Inbox buckets",
            subtitle = "Optional notification folders inside the repo.",
            items = snapshot.inboxBuckets.ifEmpty { listOf("No inbox folders found yet") },
        )
        SummarySection(
            title = "Memory context",
            subtitle = "Indexed memory notes and recent retrieval hints from the shared bus.",
            items = snapshot.memoryContext.ifEmpty { listOf("No memory index found yet") },
        )
        MemoryWorkspaceSection(
            memoryEntries = snapshot.memoryEntries,
            query = memorySearchQuery,
            onQueryChange = { memorySearchQuery = it },
            selectedMemoryId = selectedMemoryId,
            onSelectEntry = { entry ->
                selectedMemoryId = entry.memoryId
                memoryTitle = entry.title
                memorySummary = entry.summary
                memoryTags = entry.tags.ifBlank { "android, manual" }
                memorySourcePath = entry.sourcePath.ifBlank { "android-app" }
                memorySearchQuery = entry.title
                memoryStatus = "Loaded ${entry.memoryId} for editing."
            },
            title = memoryTitle,
            onTitleChange = { memoryTitle = it },
            summary = memorySummary,
            onSummaryChange = { memorySummary = it },
            tags = memoryTags,
            onTagsChange = { memoryTags = it },
            sourcePath = memorySourcePath,
            onSourcePathChange = { memorySourcePath = it },
            statusMessage = memoryStatus,
            canWrite = repoTreeUri != null,
            onSave = {
                if (repoTreeUri == null) {
                    memoryStatus = "Pick a repo folder first."
                } else {
                    val result = writeMemoryNote(
                        context = context,
                        treeUri = repoTreeUri,
                        title = memoryTitle,
                        summary = memorySummary,
                        tags = memoryTags,
                        sourcePath = memorySourcePath,
                        existingMemoryId = selectedMemoryId.ifBlank { null },
                        existingNotePath = snapshot.memoryEntries.firstOrNull { it.memoryId == selectedMemoryId }?.notePath?.ifBlank { null },
                    )
                    memoryStatus = result
                    if (result.startsWith("Saved")) {
                        selectedMemoryId = ""
                        refreshNonce++
                    }
                }
            },
        )
        MemoryDetailCard(
            selectedEntry = selectedMemoryEntry,
            noteBody = selectedMemoryBody,
            onClearSelection = {
                selectedMemoryId = ""
                memoryStatus = "Selection cleared."
            },
        )
        SummarySection(
            title = "Live files",
            subtitle = "A small sample of real files detected in the tree.",
            items = snapshot.sampleFiles.ifEmpty { listOf("No files detected yet") },
        )
    }
}

@Composable
private fun EmptyRepoHint() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("No folder selected yet", style = MaterialTheme.typography.titleMedium)
            Text(
                text = "Tap Choose folder and select a local clone or synced AgentBus tree. The browser, memory index, and write-back controls become active after permission is granted.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun RepoStatusCard(
    snapshot: RepoSnapshot,
    repoTreeUriString: String,
    onPickFolder: () -> Unit,
    onRefresh: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.extraLarge,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)),
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(snapshot.title, style = MaterialTheme.typography.titleLarge)
            Text(snapshot.statusMessage, style = MaterialTheme.typography.bodyMedium)
            if (repoTreeUriString.isNotBlank()) {
                Text(
                    text = repoTreeUriString,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                AssistChip(onClick = onPickFolder, label = { Text("Choose folder") }, leadingIcon = { androidx.compose.material3.Icon(Icons.Filled.FolderOpen, contentDescription = null) })
                AssistChip(onClick = onRefresh, label = { Text("Refresh") })
            }
        }
    }
}

@Composable
private fun SummarySection(
    title: String,
    subtitle: String,
    items: List<String>,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionHeader(title = title, subtitle = subtitle)
        items.forEach { item ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = MaterialTheme.shapes.large,
            ) {
                Text(
                    text = item,
                    modifier = Modifier.padding(16.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

@Composable
private fun SectionHeader(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private data class RepoSnapshot(
    val title: String,
    val statusMessage: String,
    val agentHandles: List<String>,
    val taskBuckets: List<String>,
    val resultBuckets: List<String>,
    val inboxBuckets: List<String>,
    val memoryContext: List<String>,
    val memoryEntries: List<MemoryIndexEntry>,
    val sampleFiles: List<String>,
) {
    companion object {
        fun empty(): RepoSnapshot = RepoSnapshot(
            title = "No repo selected",
            statusMessage = "Pick a folder to view live AgentBus files.",
            agentHandles = emptyList(),
            taskBuckets = emptyList(),
            resultBuckets = emptyList(),
            inboxBuckets = emptyList(),
            memoryContext = emptyList(),
            memoryEntries = emptyList(),
            sampleFiles = emptyList(),
        )
    }
}

private fun loadRepoSnapshot(context: Context, treeUri: Uri?): RepoSnapshot {
    if (treeUri == null) {
        return RepoSnapshot.empty()
    }

    val root = DocumentFile.fromTreeUri(context, treeUri) ?: return RepoSnapshot(
        title = "Unavailable",
        statusMessage = "Android could not open the selected folder.",
        agentHandles = emptyList(),
        taskBuckets = emptyList(),
        resultBuckets = emptyList(),
        inboxBuckets = emptyList(),
        memoryContext = emptyList(),
        memoryEntries = emptyList(),
        sampleFiles = emptyList(),
    )

    val repoRoot = resolveAgentBusRoot(root)
    val repoLabel = repoRoot.name ?: root.name ?: "Selected folder"
    val tasksFolder = findDescendantFolder(repoRoot, "tasks")
    val resultsFolder = findDescendantFolder(repoRoot, "results")
    val inboxFolder = findDescendantFolder(repoRoot, "inbox")
    val memoryFolder = findDescendantFolder(repoRoot, "memory")
    val configFolder = findDescendantFolder(repoRoot, "config")
    val agentsFile = configFolder?.let { findDescendantFile(it, "agents.yaml") }
    val memoryIndexFile = memoryFolder?.let { findDescendantFolder(it, "index") }?.let { findDescendantFile(it, "memory-index.json") }
    val registryText = agentsFile?.let { readText(context, it) }.orEmpty()
    val memoryEntries = memoryIndexFile?.let { readMemoryIndex(context, it) }.orEmpty()

    val inferredHandles = parseAgentHandles(registryText)
    val taskBuckets = summarizeBuckets(tasksFolder, "task")
    val resultBuckets = summarizeBuckets(resultsFolder, "result")
    val inboxBuckets = summarizeBuckets(inboxFolder, "inbox")
    val memoryContext = summarizeMemory(memoryEntries, memoryFolder)
    val liveFiles = sampleFiles(tasksFolder, resultsFolder, inboxFolder, agentsFile)

    return RepoSnapshot(
        title = repoLabel,
        statusMessage = if (repoRoot === root) {
            "Live AgentBus data loaded from the selected folder."
        } else {
            "Live AgentBus data loaded from the agent_bus folder inside the selected tree."
        },
        agentHandles = inferredHandles.ifEmpty { inferHandlesFromFolders(tasksFolder, resultsFolder) },
        taskBuckets = taskBuckets,
        resultBuckets = resultBuckets,
        inboxBuckets = inboxBuckets,
        memoryContext = memoryContext,
        memoryEntries = memoryEntries,
        sampleFiles = liveFiles,
    )
}

private fun resolveAgentBusRoot(root: DocumentFile): DocumentFile {
    findDescendantFolder(root, "agent_bus")?.let { return it }
    return root
}

private fun findDescendantFolder(root: DocumentFile, name: String): DocumentFile? {
    return root.listFiles().firstOrNull { it.isDirectory && it.name == name }
}

private fun findDescendantFile(root: DocumentFile, name: String): DocumentFile? {
    return root.listFiles().firstOrNull { it.isFile && it.name == name }
}

private fun readText(context: Context, file: DocumentFile): String? {
    context.contentResolver.openInputStream(file.uri)?.bufferedReader().use { reader ->
        return reader?.readText()
    }
}

private fun parseAgentHandles(registryText: String): List<String> {
    if (registryText.isBlank()) {
        return emptyList()
    }

    val handles = linkedSetOf<String>()
    var inAgentsBlock = false
    registryText.lineSequence().forEach { rawLine ->
        val line = rawLine.trimEnd()
        if (line == "agents:") {
            inAgentsBlock = true
            return@forEach
        }
        if (!inAgentsBlock) return@forEach
        val match = Regex("^([A-Za-z0-9_-]+):\\s*$").find(line.trimStart())
        if (match != null && rawLine.startsWith("  ")) {
            handles += match.groupValues[1]
        }
    }
    return handles.toList()
}

private fun inferHandlesFromFolders(tasksFolder: DocumentFile?, resultsFolder: DocumentFile?): List<String> {
    val handles = linkedSetOf<String>()
    tasksFolder?.listFiles()?.forEach { child ->
        if (child.isDirectory && !child.name.isNullOrBlank()) {
            handles += child.name!!
        }
    }
    resultsFolder?.listFiles()?.forEach { child ->
        if (child.isDirectory && !child.name.isNullOrBlank()) {
            handles += child.name!!
        }
    }
    return handles.toList()
}

private fun summarizeBuckets(folder: DocumentFile?, label: String): List<String> {
    if (folder == null) {
        return emptyList()
    }

    return folder.listFiles()
        .filter { it.isDirectory }
        .sortedBy { it.name.orEmpty() }
        .map { child ->
            val count = countFiles(child)
            "${child.name ?: "unknown"}: $count $label file${if (count == 1) "" else "s"}"
        }
}

private fun sampleFiles(
    tasksFolder: DocumentFile?,
    resultsFolder: DocumentFile?,
    inboxFolder: DocumentFile?,
    agentsFile: DocumentFile?,
): List<String> {
    val samples = mutableListOf<String>()
    tasksFolder?.listFiles()?.firstOrNull()?.name?.let { samples += "tasks/$it" }
    resultsFolder?.listFiles()?.firstOrNull()?.name?.let { samples += "results/$it" }
    inboxFolder?.listFiles()?.firstOrNull()?.name?.let { samples += "inbox/$it" }
    agentsFile?.name?.let { samples += "config/$it" }
    return samples.distinct()
}

private fun summarizeMemory(entries: List<MemoryIndexEntry>, memoryFolder: DocumentFile?): List<String> {
    if (entries.isNotEmpty()) {
        val lines = mutableListOf<String>()
        lines += "${entries.size} indexed memory note${if (entries.size == 1) "" else "s"}"
        entries.take(4).forEach { entry ->
            val summary = entry.summary.takeIf { it.isNotBlank() } ?: "No summary"
            val tags = entry.tags.takeIf { it.isNotBlank() }?.let { " | tags: $it" }.orEmpty()
            lines += "${entry.title}: $summary (${entry.sourceType}: ${entry.sourcePath})$tags"
        }
        return lines
    }

    val noteFolder = memoryFolder?.let { findDescendantFolder(it, "notes") }
    if (noteFolder == null) {
        return emptyList()
    }

    val notes = noteFolder.listFiles()
        .filter { it.isFile && it.name?.startsWith("MEMORY-") == true }
        .sortedBy { it.name.orEmpty() }
        .take(4)
        .map { file -> file.name ?: "memory note" }
        .toList()
    return if (notes.isEmpty()) emptyList() else listOf("${notes.size} memory note file${if (notes.size == 1) "" else "s"}") + notes
}

private fun readMemoryIndex(context: Context, file: DocumentFile): List<MemoryIndexEntry> {
    val text = readText(context, file).orEmpty()
    if (text.isBlank()) return emptyList()

    val entries = mutableListOf<MemoryIndexEntry>()
    runCatching {
        val root = JSONObject(text)
        val array = root.optJSONArray("entries") ?: JSONArray()
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            entries += MemoryIndexEntry(
                memoryId = item.optString("memory_id"),
                title = item.optString("title"),
                sourceType = item.optString("source_type"),
                sourcePath = item.optString("source_path"),
                summary = item.optString("summary"),
                tags = item.optString("tags"),
                notePath = item.optString("note_path"),
            )
        }
    }
    return entries
}

private fun countFiles(folder: DocumentFile): Int {
    if (folder.isFile) return 1
    return folder.listFiles().sumOf { child -> 
        if (child.isFile) 1 else countFiles(child)
    }
}
