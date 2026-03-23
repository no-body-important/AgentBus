package com.agentbus.mobile

import android.content.Context
import android.net.Uri
import android.os.Build
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.documentfile.provider.DocumentFile
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MemoryWorkspaceSection(
    memoryEntries: List<MemoryIndexEntry>,
    query: String,
    onQueryChange: (String) -> Unit,
    selectedMemoryId: String,
    onSelectEntry: (MemoryIndexEntry) -> Unit,
    title: String,
    onTitleChange: (String) -> Unit,
    summary: String,
    onSummaryChange: (String) -> Unit,
    tags: String,
    onTagsChange: (String) -> Unit,
    sourcePath: String,
    onSourcePathChange: (String) -> Unit,
    statusMessage: String,
    canWrite: Boolean,
    onSave: () -> Unit,
    ) {
    val filteredEntries = remember(memoryEntries, query) {
        filterMemoryEntries(memoryEntries, query)
    }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        MemorySectionHeader(
            title = "Memory workspace",
            subtitle = "Search the index and write a new memory note directly into the selected repo.",
        )

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = MaterialTheme.shapes.large,
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = query,
                    onValueChange = onQueryChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Search memory") },
                    placeholder = { Text("routing ledger, Android, trace id") },
                    singleLine = true,
                )
                if (filteredEntries.isEmpty()) {
                    Text(
                        text = "No memory matches yet.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    filteredEntries.take(5).forEach { entry ->
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            TextButton(onClick = { onSelectEntry(entry) }) {
                                Text(if (entry.memoryId == selectedMemoryId) "Selected: ${entry.title}" else entry.title)
                            }
                            Text(
                                text = "${entry.sourceType}: ${entry.sourcePath}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                            if (entry.summary.isNotBlank()) {
                                Text(entry.summary, style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }
            }
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = MaterialTheme.shapes.large,
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)),
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Write memory note", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = title,
                    onValueChange = onTitleChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Title") },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = summary,
                    onValueChange = onSummaryChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Summary") },
                    minLines = 2,
                    maxLines = 4,
                )
                OutlinedTextField(
                    value = tags,
                    onValueChange = onTagsChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Tags") },
                    placeholder = { Text("android, manual, routing") },
                    singleLine = true,
                )
                OutlinedTextField(
                    value = sourcePath,
                    onValueChange = onSourcePathChange,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Source path") },
                    placeholder = { Text("android-app or agent_bus/tasks/...") },
                    singleLine = true,
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = onSave, enabled = canWrite) { Text("Save note") }
                    TextButton(onClick = { onQueryChange(title.ifBlank { summary }) }) {
                        Text("Search this")
                    }
                }
                if (statusMessage.isNotBlank()) {
                    Text(
                        text = statusMessage,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

data class MemoryIndexEntry(
    val memoryId: String,
    val title: String,
    val sourceType: String,
    val sourcePath: String,
    val summary: String,
    val tags: String,
    val notePath: String,
)

fun filterMemoryEntries(entries: List<MemoryIndexEntry>, query: String): List<MemoryIndexEntry> {
    val normalized = query.trim().lowercase(Locale.US)
    if (normalized.isBlank()) {
        return entries
    }
    val tokens = normalized.split(Regex("\\s+")).filter { it.isNotBlank() }
    return entries.filter { entry ->
        val haystack = listOf(
            entry.memoryId,
            entry.title,
            entry.sourceType,
            entry.sourcePath,
            entry.summary,
            entry.tags,
        ).joinToString(" ").lowercase(Locale.US)
        tokens.all { token -> haystack.contains(token) }
    }
}

fun writeMemoryNote(
    context: Context,
    treeUri: Uri,
    title: String,
    summary: String,
    tags: String,
    sourcePath: String,
    existingMemoryId: String? = null,
    existingNotePath: String? = null,
): String {
    val root = DocumentFile.fromTreeUri(context, treeUri) ?: return "Could not open the selected folder."
    val repoRoot = resolveAgentBusRoot(root)
    val memoryRoot = ensureChildDirectory(repoRoot, "memory") ?: return "Could not create agent_bus/memory."
    val notesRoot = ensureChildDirectory(memoryRoot, "notes") ?: return "Could not create agent_bus/memory/notes."
    val indexRoot = ensureChildDirectory(memoryRoot, "index") ?: return "Could not create agent_bus/memory/index."

    val noteTitle = title.trim().ifBlank { "Untitled memory" }
    val noteSummary = summary.trim().ifBlank { "No summary provided." }
    val tagList = parseTags(tags)
    val createdAt = nowUtcIso()
    val memoryId = existingMemoryId?.takeIf { it.isNotBlank() } ?: buildMemoryId("android", noteTitle, createdAt)
    val cleanSourcePath = sourcePath.trim().ifBlank { "android-app" }
    val noteFile = findMemoryNoteFile(notesRoot, existingNotePath, memoryId) ?: notesRoot.createFile("text/markdown", "$memoryId.md")
    if (noteFile == null) {
        return "Could not create memory note file."
    }
    val noteBody = buildMemoryNoteMarkdown(
        memoryId = memoryId,
        title = noteTitle,
        summary = noteSummary,
        authorAgent = "android",
        createdAt = createdAt,
        sourcePath = cleanSourcePath,
        tags = tagList,
    )
    if (!writeDocumentText(context, noteFile, noteBody)) {
        return "Could not write the memory note."
    }

    val indexFile = indexRoot.findFile("memory-index.json") ?: indexRoot.createFile("application/json", "memory-index.json")
    if (indexFile != null) {
        writeMemoryIndexEntry(
            context = context,
            indexFile = indexFile,
            memoryId = memoryId,
            title = noteTitle,
            notePath = "memory/notes/${noteFile.name ?: "$memoryId.md"}",
            sourceType = "manual",
            summary = noteSummary,
            tags = tagList,
            sourceTraceId = memoryId,
            authorAgent = "android",
            createdAt = createdAt,
        )
    }

    return "Saved $memoryId"
}

private fun ensureChildDirectory(root: DocumentFile, name: String): DocumentFile? {
    root.findFile(name)?.let { if (it.isDirectory) return it }
    return root.createDirectory(name)
}

private fun resolveAgentBusRoot(root: DocumentFile): DocumentFile {
    findDescendantFolder(root, "agent_bus")?.let { return it }
    return root
}

private fun findDescendantFolder(root: DocumentFile, name: String): DocumentFile? {
    return root.listFiles().firstOrNull { it.isDirectory && it.name == name }
}

private fun writeDocumentText(context: Context, file: DocumentFile, text: String): Boolean {
    return runCatching {
        context.contentResolver.openOutputStream(file.uri, "wt")?.bufferedWriter().use { writer ->
            writer?.write(text)
            writer?.flush()
        }
        true
    }.getOrDefault(false)
}

private fun readText(context: Context, file: DocumentFile): String? {
    context.contentResolver.openInputStream(file.uri)?.bufferedReader().use { reader ->
        return reader?.readText()
    }
}

private fun findMemoryNoteFile(notesRoot: DocumentFile, existingNotePath: String?, memoryId: String): DocumentFile? {
    val candidates = listOfNotNull(
        existingNotePath?.substringAfterLast('/'),
        "$memoryId.md",
    ).distinct()
    for (candidate in candidates) {
        notesRoot.findFile(candidate)?.let { return it }
    }
    return null
}

private fun buildMemoryNoteMarkdown(
    memoryId: String,
    title: String,
    summary: String,
    authorAgent: String,
    createdAt: String,
    sourcePath: String,
    tags: List<String>,
): String {
    val yamlTags = if (tags.isEmpty()) "  - android" else tags.joinToString("\n") { "  - $it" }
    return """
---
memory_id: $memoryId
title: ${escapeYamlScalar(title)}
memory_type: observation
author_agent: $authorAgent
created_at: $createdAt
updated_at: $createdAt
source_type: manual
source_path: ${escapeYamlScalar(sourcePath)}
source_trace_id: $memoryId
importance: normal
tags:
$yamlTags
related_artifacts:
  - memory/index/memory-index.json
summary: ${escapeYamlScalar(summary)}
body_hint: observation
---

## Summary
$summary

## Notes
- Added from the Android app.
- Tags: ${if (tags.isEmpty()) "android" else tags.joinToString(", ")}
""".trimIndent()
}

private fun writeMemoryIndexEntry(
    context: Context,
    indexFile: DocumentFile,
    memoryId: String,
    title: String,
    notePath: String,
    sourceType: String,
    summary: String,
    tags: List<String>,
    sourceTraceId: String,
    authorAgent: String,
    createdAt: String,
) {
    val existing = readText(context, indexFile).orEmpty()
    val root = runCatching {
        if (existing.isBlank()) JSONObject().put("entries", JSONArray())
        else JSONObject(existing)
    }.getOrElse { JSONObject().put("entries", JSONArray()) }
    val entries = root.optJSONArray("entries") ?: JSONArray().also { root.put("entries", it) }
    val entry = JSONObject().apply {
        put("dedupe_key", listOf("observation", sourceType, notePath, sourceTraceId, authorAgent).joinToString("|").lowercase(Locale.US))
        put("memory_id", memoryId)
        put("note_path", notePath)
        put("title", title)
        put("memory_type", "observation")
        put("author_agent", authorAgent)
        put("source_type", sourceType)
        put("source_path", notePath)
        put("source_trace_id", sourceTraceId)
        put("summary", summary)
        put("updated_at", createdAt)
        put("tags", tags.joinToString(", "))
    }

    val replaced = mutableListOf<JSONObject>()
    var updated = false
    for (i in 0 until entries.length()) {
        val item = entries.optJSONObject(i) ?: continue
        if (item.optString("dedupe_key") == entry.optString("dedupe_key")) {
            replaced += entry
            updated = true
        } else {
            replaced += item
        }
    }
    if (!updated) {
        replaced += entry
    }
    replaced.sortBy { it.optString("memory_id") }
    val next = JSONArray()
    replaced.forEach { next.put(it) }
    root.put("entries", next)
    writeDocumentText(context, indexFile, root.toString(2))
}

private fun nowUtcIso(): String {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        java.time.OffsetDateTime.now(java.time.ZoneOffset.UTC).toString()
    } else {
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(Date())
    }
}

private fun buildMemoryId(prefix: String, title: String, createdAtIso: String): String {
    val stamp = createdAtIso.replace(":", "").replace("-", "").replace("T", "-").take(15)
    val slug = slugify("$prefix-$title").take(48)
    return "MEMORY-$stamp-$slug"
}

private fun slugify(text: String): String {
    return text.trim().lowercase(Locale.US).replace(Regex("[^a-z0-9]+"), "-").trim('-').ifBlank { "note" }
}

private fun parseTags(tags: String): List<String> {
    return tags.split(',').map { it.trim() }.filter { it.isNotBlank() }.distinct()
}

private fun escapeYamlScalar(value: String): String {
    if (value.isBlank()) return "\"\""
    if (value.any { it.isWhitespace() || it in listOf(':', '#', '"', '\'') }) {
        return "\"" + value.replace("\"", "\\\"") + "\""
    }
    return value
}

@Composable
private fun MemorySectionHeader(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
